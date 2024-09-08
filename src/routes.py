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


def get_mysql_info():
    mysql_manager = MySQLManager()
    try:
        mysql_manager.connect()

        # Get list of tables
        tables = mysql_manager.execute_query("SHOW TABLES")
        if not isinstance(tables, list):
            raise ValueError(f"Unexpected result type: {type(tables)}")
        if len(tables) == 0:
            return {
                'database_size_mb': 0,
                'total_rows': 0,
                'tables': [],
                'profiles_scanned': 0,
                'companies_scanned': 0,
                'error': "No tables found in the database"
            }

        table_info = []
        total_rows = 0
        total_size_mb = 0
        profiles_scanned = 0
        companies_scanned = 0

        for table in tables:
            table_name = list(table.values())[0]
            try:
                # Get row count for each table
                row_count_result = mysql_manager.execute_query(
                    f"SELECT COUNT(*) as row_count FROM `{table_name}`"
                )
                if not isinstance(row_count_result, list) or len(row_count_result) == 0:
                    raise ValueError(f"Failed to get row count for table {table_name}")
                row_count = row_count_result[0]['row_count']
                total_rows += row_count

                # Update profiles_scanned and companies_scanned
                if table_name == 'linkedin_people':
                    profiles_scanned = row_count
                elif table_name == 'linkedin_companies':
                    companies_scanned = row_count

                # Get table size
                status_result = mysql_manager.execute_query(
                    f"SHOW TABLE STATUS LIKE '{table_name}'"
                )
                if not isinstance(status_result, list) or len(status_result) == 0:
                    raise ValueError(f"Failed to get table status for {table_name}")
                status = status_result[0]
                size_mb = (status['Data_length'] + status['Index_length']) / (1024 * 1024)
                total_size_mb += size_mb

                table_info.append({
                    'table_name': table_name,
                    'row_count': row_count,
                    'size_mb': round(size_mb, 2)
                })
            except Exception as table_error:
                print(f"Error getting info for table {table_name}: {str(table_error)}")
                table_info.append({
                    'table_name': table_name,
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
    except MySQLError as e:
        print(f"MySQL Error: {str(e)}")
        return {
            'database_size_mb': 0,
            'total_rows': 0,
            'tables': [],
            'profiles_scanned': 0,
            'companies_scanned': 0,
            'error': f"MySQL Error: {str(e)}"
        }
    except Exception as e:
        print(f"Error retrieving MySQL info: {str(e)}")
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
        nats_manager = NatsManager.get_instance()
        mysql_manager = MySQLManager()

        try:
            nats_manager.connect()
            nats_status = "Connected"
            nats_error = None
        except Exception as e:
            nats_status = "Disconnected"
            nats_error = str(e)

        try:
            mysql_manager.connect()
            mysql_status = "Connected"
            mysql_error = None
        except Exception as e:
            mysql_status = "Disconnected"
            mysql_error = str(e)

        crawler_status = "Running" if crawler_state.is_running() else "Stopped"
        mysql_info = get_mysql_info()
        
        # Fetch latest profiles and companies
        try:
            mysql_manager.connect()
            latest_entries = mysql_manager.execute_query("""
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
            """)
        except Exception as e:
            log(f"Error fetching latest entries: {str(e)}", "error")
            latest_entries = []
        finally:
            mysql_manager.disconnect()

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
            return redirect(url_for('index'))
        except Exception as e:
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
            return redirect(url_for('index'))
        except Exception as e:
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
    def table_view(table_name):
        page = request.args.get('page', 1, type=int)
        per_page = 20
        sort_by = request.args.get('sort_by', 'id')
        sort_order = request.args.get('sort_order', 'asc')

        mysql_manager = MySQLManager()
        try:
            mysql_manager.connect()
            
            # Get total number of records
            count_result = mysql_manager.execute_query(f"SELECT COUNT(*) as count FROM {table_name}")
            total_records = count_result[0]['count']
            
            # Calculate pagination
            total_pages = ceil(total_records / per_page)
            offset = (page - 1) * per_page

            # Get records with sorting and pagination
            query = f"SELECT * FROM {table_name} ORDER BY {sort_by} {sort_order} LIMIT {per_page} OFFSET {offset}"
            records = mysql_manager.execute_query(query)

            # Get column names
            columns = mysql_manager.execute_query(f"SHOW COLUMNS FROM {table_name}")
            column_names = [column['Field'] for column in columns]

            return render_template('table_view.html', 
                                   table_name=table_name, 
                                   records=records, 
                                   columns=column_names,
                                   page=page, 
                                   total_pages=total_pages,
                                   sort_by=sort_by,
                                   sort_order=sort_order)
        finally:
            mysql_manager.disconnect()

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
            is_seed = True  # Always treat manually added URLs as seed profiles
            
            try:
                # Add to NATS
                nats_manager = NatsManager.get_instance()
                nats_manager.connect()
                
                subject = f"linkedin_{url_type}_urls"
                message = json.dumps({"url": url, "is_seed": is_seed})
                nats_manager.publish(subject, message)
                log(f"Added seed {url_type} URL to NATS: {url}")
                
                # Add to seed_urls table
                mysql_manager = MySQLManager()
                try:
                    mysql_manager.connect()
                    query = """
                        INSERT INTO seed_urls (url, type)
                        VALUES (%s, %s)
                        ON DUPLICATE KEY UPDATE type = VALUES(type)
                    """
                    mysql_manager.execute_query(query, (url, url_type))
                    log(f"Added seed {url_type} URL to database: {url}")
                except Exception as e:
                    log(f"Error adding seed URL to database: {str(e)}", "error")
                    flash(f"Error adding URL to database: {str(e)}", 'error')
                    return redirect(url_for('add_url'))
                finally:
                    mysql_manager.disconnect()

                flash('URL added successfully', 'success')
                return redirect(url_for('index'))
            except Exception as e:
                log(f"Error adding URL: {str(e)}", "error")
                flash(f"Error adding URL: {str(e)}", 'error')
                return redirect(url_for('add_url'))
        
        return render_template('add_url.html')

    return app
