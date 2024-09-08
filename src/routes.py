from flask import (  # noqa: E501
    render_template, request, redirect, url_for, jsonify, send_file, flash
)
from shared_data import log, activity_queue
from mysql_manager import MySQLManager
from nats_manager import NatsManager
import csv
import io
import asyncio
from crawler_manager import start_crawler, stop_crawler, crawler_state
from contextlib import contextmanager
from mysql.connector import Error as MySQLError
import json
from math import ceil

@contextmanager
def nats_connection():
    nats_manager = NatsManager.get_instance()
    try:
        nats_manager.connect()
        yield nats_manager
    except Exception as e:
        print(f"Error connecting to NATS: {e}")
        yield None
    finally:
        if nats_manager:
            nats_manager.close()

def check_nats_health():
    try:
        nats_manager = NatsManager.get_instance()
        nats_manager.connect()
        return "Connected", None
    except Exception as e:
        return "Error", str(e)

def check_mysql_health():
    mysql_manager = MySQLManager()
    try:
        mysql_manager.connect()
        mysql_manager.disconnect()
        return "Connected", None
    except Exception as e:
        return "Disconnected", str(e)

async def get_mysql_info(mysql_manager):
    try:
        await mysql_manager.connect()
        # Fetch database size
        size_query = "SELECT SUM(data_length + index_length) / 1024 / 1024 AS size_mb FROM information_schema.tables WHERE table_schema = %s"
        size_result = await mysql_manager.execute_query(size_query, (mysql_manager.db_config['db'],))
        database_size_mb = size_result[0]['size_mb'] if size_result[0]['size_mb'] is not None else 0

        # Fetch total number of rows
        tables_query = "SHOW TABLES"
        tables = await mysql_manager.execute_query(tables_query)
        total_rows = 0
        table_info = []
        for table in tables:
            table_name = list(table.values())[0]
            count_query = f"SELECT COUNT(*) as count FROM {table_name}"
            count_result = await mysql_manager.execute_query(count_query)
            row_count = count_result[0]['count']
            total_rows += row_count
            table_info.append({'name': table_name, 'rows': row_count})

        # Fetch profiles and companies scanned
        profiles_query = "SELECT COUNT(*) as count FROM linkedin_people"
        companies_query = "SELECT COUNT(*) as count FROM linkedin_companies"
        profiles_result = await mysql_manager.execute_query(profiles_query)
        companies_result = await mysql_manager.execute_query(companies_query)
        profiles_scanned = profiles_result[0]['count']
        companies_scanned = companies_result[0]['count']

        return {
            'database_size_mb': round(database_size_mb, 2),
            'total_rows': total_rows,
            'tables': table_info,
            'profiles_scanned': profiles_scanned,
            'companies_scanned': companies_scanned
        }
    except Exception as e:
        log(f"Error in get_mysql_info: {str(e)}", "error")
        return {
            'database_size_mb': 0,
            'total_rows': 0,
            'tables': [],
            'profiles_scanned': 0,
            'companies_scanned': 0,
            'error': str(e)
        }
    finally:
        await mysql_manager.disconnect()

async def get_latest_entries(mysql_manager):
    try:
        await mysql_manager.connect()
        query = """
            (SELECT 'person' as type, name, linkedin_url, created_at
             FROM linkedin_people
             ORDER BY created_at DESC
             LIMIT 10)
            UNION ALL
            (SELECT 'company' as type, name, linkedin_url, created_at
             FROM linkedin_companies
             ORDER BY created_at DESC
             LIMIT 10)
            ORDER BY created_at DESC
            LIMIT 20
        """
        return await mysql_manager.execute_query(query)
    except Exception as e:
        log(f"Error fetching latest entries: {str(e)}", "error")
        return []
    finally:
        await mysql_manager.disconnect()

def register_routes(app):
    @app.route('/', methods=['GET'])
    async def index():
        nats_manager = NatsManager.get_instance()
        mysql_manager = MySQLManager()

        async def async_operations():
            try:
                await nats_manager.connect()
                nats_status = "Connected"
                nats_error = None
            except Exception as e:
                log(f"Error connecting to NATS in index route: {str(e)}", "error")
                nats_status = "Disconnected"
                nats_error = str(e)
            return nats_status, nats_error

        nats_status, nats_error = await async_operations()

        try:
            await mysql_manager.connect()
            mysql_status = "Connected"
            mysql_error = None
        except Exception as e:
            log(f"Error connecting to MySQL in index route: {str(e)}", "error")
            mysql_status = "Disconnected"
            mysql_error = str(e)

        crawler_status = "Running" if crawler_state.is_running() else "Stopped"

        # Fetch MySQL info and latest entries concurrently
        mysql_info, latest_entries = await asyncio.gather(
            get_mysql_info(mysql_manager),
            get_latest_entries(mysql_manager)
        )

        return render_template('index.html',
                               nats_status=nats_status,
                               nats_error=nats_error,
                               mysql_status=mysql_status,
                               mysql_error=mysql_error,
                               crawler_status=crawler_status,
                               mysql_info=mysql_info,
                               latest_entries=latest_entries,
                               profiles_scanned=mysql_info['profiles_scanned'],
                               companies_scanned=mysql_info['companies_scanned'])
    @app.route('/start_crawler', methods=['POST'])
    def start_crawler_route():
        try:
            if not crawler_state.is_running():
                start_crawler()
                flash('Crawler started successfully', 'success')
            else:
                flash('Crawler is already running', 'info')
        except Exception as e:
            log(f"Error starting crawler: {str(e)}", "error")
            flash(f'Error starting crawler: {str(e)}', 'error')
        return redirect(url_for('index'))

    @app.route('/stop_crawler', methods=['POST'])
    def stop_crawler_route():
        try:
            if crawler_state.is_running():
                stop_crawler()
                flash('Crawler stopped successfully', 'success')
            else:
                flash('Crawler is not running', 'info')
        except Exception as e:
            log(f"Error stopping crawler: {str(e)}", "error")
            flash(f'Error stopping crawler: {str(e)}', 'error')
        return redirect(url_for('index'))

    @app.route('/status', methods=['GET'])
    def status():
        mysql_info = get_mysql_info()
        nats_status, nats_error = check_nats_health()
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

    @app.route('/tables')
    def list_tables():
        mysql_info = get_mysql_info()
        return render_template('tables.html', 
                               tables=mysql_info['tables'],
                               database_size_mb=mysql_info['database_size_mb'],
                               total_rows=mysql_info['total_rows'])

    @app.route('/table/<table_name>')
    async def table_view(table_name):
        page = request.args.get('page', 1, type=int)
        per_page = 20
        sort_by = request.args.get('sort_by', 'id')
        sort_order = request.args.get('sort_order', 'asc')

        mysql_manager = MySQLManager()
        try:
            await mysql_manager.connect()
            
            # Get total number of records
            count_query = f"SELECT COUNT(*) as count FROM {table_name}"
            count_result = await mysql_manager.execute_query(count_query)
            
            if not count_result or 'count' not in count_result[0]:
                raise ValueError(f"Unexpected count result: {count_result}")
            
            total_records = count_result[0]['count']
            
            # Calculate pagination
            total_pages = ceil(total_records / per_page)
            offset = (page - 1) * per_page

            # Get records with sorting and pagination
            query = f"SELECT * FROM {table_name} ORDER BY {sort_by} {sort_order} LIMIT {per_page} OFFSET {offset}"
            records = await mysql_manager.execute_query(query)

            # Get column names
            columns_query = f"SHOW COLUMNS FROM {table_name}"
            columns = await mysql_manager.execute_query(columns_query)
            column_names = [column['Field'] for column in columns]

            return render_template('table_view.html', 
                                table_name=table_name, 
                                records=records, 
                                columns=column_names,
                                page=page, 
                                total_pages=total_pages,
                                sort_by=sort_by,
                                sort_order=sort_order,
                                total_records=total_records)
        except Exception as e:
            log(f"Error in table_view for {table_name}: {str(e)}", "error")
            flash(f"Error viewing table: {str(e)}", 'error')
            return redirect(url_for('list_tables'))
        finally:
            await mysql_manager.disconnect()

    @app.route('/table/<table_name>/add', methods=['GET', 'POST'])
    def add_record(table_name):
        mysql_manager = MySQLManager()
        try:
            mysql_manager.connect()
            
            if request.method == 'POST':
                columns = ', '.join(request.form.keys())
                placeholders = ', '.join(['%s'] * len(request.form))
                query = f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders})"
                values = tuple(request.form.values())
                mysql_manager.execute_query(query, values)
                flash('Record added successfully', 'success')
                return redirect(url_for('table_view', table_name=table_name))

            # Get column names for the form
            columns = mysql_manager.execute_query(f"SHOW COLUMNS FROM {table_name}")
            return render_template('add_record.html', table_name=table_name, columns=columns)
        finally:
            mysql_manager.disconnect()

    @app.route('/table/<table_name>/edit/<int:id>', methods=['GET', 'POST'])
    def edit_record(table_name, id):
        mysql_manager = MySQLManager()
        try:
            mysql_manager.connect()
            
            if request.method == 'POST':
                set_clause = ', '.join([f"{key} = %s" for key in request.form.keys()])
                query = f"UPDATE {table_name} SET {set_clause} WHERE id = %s"
                values = tuple(request.form.values()) + (id,)
                mysql_manager.execute_query(query, values)
                flash('Record updated successfully', 'success')
                return redirect(url_for('table_view', table_name=table_name))

            query = f"SELECT * FROM {table_name} WHERE id = %s"
            record = mysql_manager.execute_query(query, (id,))[0]
            return render_template('edit_record.html', table_name=table_name, record=record)
        finally:
            mysql_manager.disconnect()

    @app.route('/table/<table_name>/delete/<int:id>', methods=['POST'])
    def delete_record(table_name, id):
        mysql_manager = MySQLManager()
        try:
            mysql_manager.connect()
            query = f"DELETE FROM {table_name} WHERE id = %s"
            mysql_manager.execute_query(query, (id,))
            flash('Record deleted successfully', 'success')
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

            if not records:
                flash(f"No data found in table {table_name}", 'warning')
                return redirect(url_for('table_view', table_name=table_name))

            output = io.StringIO()
            writer = csv.DictWriter(
                output,
                fieldnames=records[0].keys()
            )
            writer.writeheader()
            for record in records:
                writer.writerow(record)

            output.seek(0)
            return send_file(
                io.BytesIO(output.getvalue().encode('utf-8')),
                mimetype='text/csv',
                as_attachment=True,
                download_name=f'{table_name}.csv'  # Changed from attachment_filename to download_name
            )
        except Exception as e:
            log(f"Error exporting CSV for {table_name}: {str(e)}", "error")
            flash(f"Error exporting CSV: {str(e)}", 'error')
            return redirect(url_for('table_view', table_name=table_name))
        finally:
            mysql_manager.disconnect()

    @app.route('/add_url', methods=['GET', 'POST'])
    def add_url():
        if request.method == 'POST':
            url = request.form['url']
            url_type = request.form['type']
            is_seed = True  # Always treat manually added URLs as seed profiles
            
            nats_manager = NatsManager.get_instance()
            mysql_manager = MySQLManager()
            
            async def async_operations():
                try:
                    # Add to NATS
                    await nats_manager.connect()
                    log("Successfully connected to NATS")
                    
                    subject = f"linkedin_{url_type}_urls"
                    message = json.dumps({"url": url, "is_seed": is_seed})
                    await nats_manager.publish(subject, message)
                    log(f"Successfully added seed {url_type} URL to NATS: {url}")
                except Exception as e:
                    log(f"Error in add_url route: {str(e)}", "error")
                    raise

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(async_operations())
            except Exception as e:
                flash(f"Error adding URL to NATS: {str(e)}", 'error')
                return redirect(url_for('add_url'))
            finally:
                loop.close()
            
            # Add to seed_urls table
            try:
                mysql_manager.connect()
                log("Successfully connected to MySQL")
                
                query = """
                    INSERT INTO seed_urls (url, type)
                    VALUES (%s, %s)
                    ON DUPLICATE KEY UPDATE type = VALUES(type)
                """
                mysql_manager.execute_query(query, (url, url_type))
                log(f"Successfully added seed {url_type} URL to database: {url}")
                flash('URL added successfully', 'success')
            except Exception as e:
                log(f"Error adding seed URL to database: {str(e)}", "error")
                flash(f"Error adding URL to database: {str(e)}", 'error')
            finally:
                mysql_manager.disconnect()
                log("MySQL connection closed")
            
            return redirect(url_for('index'))
        
        return render_template('add_url.html')

    return app
