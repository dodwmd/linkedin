from flask import (  # noqa: E501
    render_template, request, redirect, url_for, jsonify, send_file
)
from shared_data import log, activity_queue
from mysql_manager import MySQLManager
from nats_manager import NatsManager
import csv
import io
import asyncio
from crawler_manager import start_crawler, stop_crawler, crawler_state
from contextlib import asynccontextmanager


@asynccontextmanager
async def nats_connection():
    try:
        nats_manager = await NatsManager.get_instance()
        yield nats_manager
    except Exception as e:
        print(f"Error connecting to NATS: {e}")
        yield None
    finally:
        if nats_manager:
            await nats_manager.close()


async def check_nats_health():
    try:
        async with asyncio.timeout(5):  # 5 seconds timeout
            async with nats_connection():
                return "Connected", None
    except asyncio.TimeoutError:
        return "Timeout", "Connection timed out"
    except Exception as e:
        return "Error", str(e)


def check_nats_health_sync():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(check_nats_health())
    finally:
        loop.close()


def check_mysql_health():
    mysql_manager = MySQLManager()
    try:
        mysql_manager.connect()
        mysql_manager.disconnect()
        return "Connected", None
    except Exception as e:
        return "Disconnected", str(e)


def get_mysql_info():
    mysql_manager = MySQLManager()
    try:
        mysql_manager.connect()

        # Get list of tables
        tables = mysql_manager.execute_query("SHOW TABLES")
        tables = [list(table.values())[0] for table in tables]

        table_info = []
        total_rows = 0
        total_size_mb = 0
        profiles_scanned = 0
        companies_scanned = 0

        for table in tables:
            try:
                # Get row count for each table
                row_count = mysql_manager.execute_query(
                    f"SELECT COUNT(*) as row_count FROM `{table}`"
                )[0]['row_count']
                total_rows += row_count

                # Update profiles_scanned and companies_scanned
                if table == 'linkedin_people':
                    profiles_scanned = row_count
                elif table == 'linkedin_companies':
                    companies_scanned = row_count

                # Get table size
                status = mysql_manager.execute_query(
                    f"SHOW TABLE STATUS LIKE '{table}'"
                )[0]
                size_mb = (
                    status['Data_length'] + status['Index_length']
                ) / (1024 * 1024)
                total_size_mb += size_mb

                table_info.append({
                    'table_name': table,
                    'row_count': row_count,
                    'size_mb': round(size_mb, 2)
                })
            except Exception as table_error:
                print(f"Error getting info for table {table}: {str(table_error)}")
                table_info.append({
                    'table_name': table,
                    'row_count': 'N/A',
                    'size_mb': 'N/A'
                })

        mysql_manager.disconnect()

        return {
            'database_size_mb': round(total_size_mb, 2),
            'total_rows': total_rows,
            'tables': table_info,
            'profiles_scanned': profiles_scanned,
            'companies_scanned': companies_scanned
        }
    except Exception as e:
        print(f"Error retrieving MySQL info: {str(e)}")  # noqa: E501
        return {
            'database_size_mb': 0,
            'total_rows': 0,
            'tables': [],
            'profiles_scanned': 0,
            'companies_scanned': 0,
            'error': str(e)
        }


def register_routes(app):
    @app.route('/', methods=['GET'])
    def index():
        nats_status, nats_error = check_nats_health_sync()
        mysql_status, mysql_error = check_mysql_health()
        crawler_status = (
            "Running" if crawler_state.is_running() else "Stopped"
        )
        mysql_info = get_mysql_info()
        nats_server_info, nats_subject_info = {}, {}

        last_logs = list(activity_queue.queue)[-50:]
        return render_template(
            'index.html',
            profiles_scanned=mysql_info['profiles_scanned'],
            companies_scanned=mysql_info['companies_scanned'],
            nats_status=nats_status,
            nats_error=nats_error,
            mysql_status=mysql_status,
            mysql_error=mysql_error,
            crawler_status=crawler_status,
            mysql_info=mysql_info,
            nats_server_info=nats_server_info,
            nats_subject_info=nats_subject_info,
            logs=last_logs
        )

    @app.route('/start_crawler', methods=['POST'])
    def start_crawler_route():
        if start_crawler():
            return jsonify({"status": "Crawler started successfully"})
        else:
            return jsonify({"status": "Crawler is already running"})

    @app.route('/stop_crawler', methods=['POST'])
    def stop_crawler_route():
        if stop_crawler():
            return jsonify({
                "status": "Crawler stop requested. "
                          "It may take a moment to fully stop."
            })
        else:
            return jsonify({"status": "Crawler is not running"})

    @app.route('/status', methods=['GET'])
    def status():
        mysql_info = get_mysql_info()
        nats_status, nats_error = check_nats_health_sync()
        mysql_status, mysql_error = check_mysql_health()

        return jsonify({
            'profiles_scanned': mysql_info['profiles_scanned'],
            'companies_scanned': mysql_info['companies_scanned'],
            'active_threads': 0,  # You may want to implement this
            'queue_size': 0,  # You may want to implement this
            'nats_status': nats_status,
            'mysql_status': mysql_status,
            'crawler_status': (
                'Running' if crawler_state.is_running() else 'Stopped'
            ),
            'mysql_info': mysql_info
        })

    @app.route('/table/<table_name>')
    def table_view(table_name):
        page = request.args.get('page', 1, type=int)
        per_page = 20
        offset = (page - 1) * per_page

        with MySQLManager() as mysql_manager:
            total_records = mysql_manager.execute_query(
                f"SELECT COUNT(*) as count FROM {table_name}"
            )[0]['count']

            records = mysql_manager.execute_query(
                f"SELECT * FROM {table_name} LIMIT {per_page} OFFSET {offset}"  # noqa: E501
            )

            # Get column names
            columns = mysql_manager.execute_query(
                f"SHOW COLUMNS FROM {table_name}"
            )
            columns = [column['Field'] for column in columns]

        total_pages = (total_records + per_page - 1) // per_page

        # Calculate the page range for pagination
        page_range = range(
            max(1, page - 2),
            min(total_pages, page + 2) + 1
        )

        return render_template(
            'table_view.html',
            table_name=table_name,
            records=records,
            columns=columns,
            page=page,
            total_pages=total_pages,
            page_range=page_range,
            total_records=total_records
        )

    @app.route('/edit/<table_name>/<int:record_id>', methods=['GET', 'POST'])
    def edit_record(table_name, record_id):
        mysql_manager = MySQLManager()
        try:
            mysql_manager.connect()

            if request.method == 'POST':
                set_clause = ', '.join(
                    [f"{key} = %s" for key in request.form.keys() if key != 'id']
                )
                query = f"UPDATE {table_name} SET {set_clause} WHERE id = %s"
                values = (
                    [request.form[key] for key in request.form.keys() if key != 'id']
                    + [record_id]
                )
                mysql_manager.execute_query(query, values)
                mysql_manager.connection.commit()
                return redirect(url_for('table_view', table_name=table_name))

            query = f"SELECT * FROM {table_name} WHERE id = %s"
            record = mysql_manager.execute_query(query, (record_id,))
            if record:
                record = record[0]
            else:
                record = None

            return render_template('edit_record.html', table_name=table_name, record=record)  # noqa: E501
        finally:
            mysql_manager.disconnect()

    @app.route('/delete/<table_name>/<int:record_id>', methods=['POST'])
    def delete_record(table_name, record_id):
        mysql_manager = MySQLManager()
        try:
            mysql_manager.connect()

            query = f"DELETE FROM {table_name} WHERE id = %s"
            mysql_manager.execute_query(query, (record_id,))
            mysql_manager.connection.commit()

            return redirect(url_for('table_view', table_name=table_name))
        finally:
            mysql_manager.disconnect()

    @app.route('/export/<table_name>')
    def export_csv(table_name):
        mysql_manager = MySQLManager()
        try:
            mysql_manager.connect()

            query = f"SELECT * FROM {table_name}"
            records = mysql_manager.execute_query(query)

            output = io.StringIO()
            writer = csv.DictWriter(
                output,
                fieldnames=records[0].keys() if records else []
            )
            writer.writeheader()
            for record in records:
                writer.writerow(record)

            output.seek(0)
            return send_file(
                io.BytesIO(output.getvalue().encode('utf-8')),
                mimetype='text/csv',
                as_attachment=True,
                attachment_filename=f'{table_name}.csv'
            )
        finally:
            mysql_manager.disconnect()

    @app.route('/add_url', methods=['GET', 'POST'])
    def add_url():
        if request.method == 'POST':
            url = request.form['url']
            url_type = request.form['type']
            mysql_manager = MySQLManager()
            try:
                mysql_manager.connect()
                table_name = (
                    'linkedin_people' if url_type == 'person'
                    else 'linkedin_companies'
                )
                query = f"INSERT INTO {table_name} (linkedin_url) VALUES (%s)"
                mysql_manager.execute_query(query, (url,))
                mysql_manager.connection.commit()
                log(f"Added {url_type} URL: {url}")
                return redirect(url_for('index'))
            except Exception as e:
                log(f"Error adding URL: {str(e)}", "error")
                return f"Error adding URL: {str(e)}", 500
            finally:
                mysql_manager.disconnect()
        return render_template('add_url.html')

    return app
