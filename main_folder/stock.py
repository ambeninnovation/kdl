from flask import Flask, render_template, request, redirect, url_for, flash, Blueprint
from dotenv import load_dotenv
import os
from supabase import create_client, Client

from datetime import datetime





stock = Blueprint('stock', __name__)

#templates for this blueprint are in the stock folder

#routes for this blueprint
#stock_dashboard
#recieve_stock
#stock_report
#sort_stock
#delivery_note
#stock_transfer
#recieveclientsstock
#stock_adjustment

#load .env file
load_dotenv()
url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(url, key)
secret = os.getenv("SECRET_KEY")


@stock.route('/stock_dashboard')
def stock_dashboard():
    return render_template('stock/stock_dashboard.html')

@stock.route('/receive_unsorted_stock', methods=['GET', 'POST'])
def receive_unsorted_stock():
    if request.method == 'POST':
        # Retrieve and validate form data
        pole_type = request.form.get('pole_type')
        supplier_id = request.form.get('supplier_id')
        quantity = request.form.get('quantity')
        description = request.form.get('description')

        # Check for missing fields
        missing_fields = []
        if not pole_type:
            missing_fields.append('Pole Type')
        if not supplier_id:
            missing_fields.append('Supplier ID')
        if not quantity:
            missing_fields.append('Quantity')
        if not description:
            missing_fields.append('Description')

        if missing_fields:
            flash(f'Missing fields: {", ".join(missing_fields)}', 'danger')
            return redirect(url_for('stock.receive_unsorted_stock'))  # Ensure this is the correct route

        # Validate numeric fields
        try:
            quantity = float(quantity)
        except ValueError:
            flash('Quantity and Supplier ID must be valid numbers.', 'danger')
            return redirect(url_for('stock.receive_unsorted_stock'))

        # Generate receipt data
        date_created = datetime.utcnow().isoformat()
        receipt_data = {
            "pole_type": pole_type,
            "supplier_id": supplier_id,
            "description": description,
            "date": date_created,
            "quantity": quantity,
        }

        # Insert receipt into Supabase
        try:
            response = supabase.table('unsorted_stock').insert(receipt_data).execute()
            if response:  # Check for successful insertion
                flash('Stock entry created successfully!', 'success')
            else:
                flash('Failed to create stock entry. Please try again.', 'danger')
        except Exception as e:
            flash(f'Error saving stock entry: {str(e)}', 'danger')

        return redirect(url_for('stock.receive_unsorted_stock'))  # Redirect to the same page after submission

    # Fetch suppliers and unsorted stock
    try:
        suppliers = supabase.table('suppliers').select("*").execute().data
        unsorted = supabase.table('unsorted_stock') .select("*").execute().data
    except Exception as e:
        flash(f'Error fetching data: {str(e)}', 'danger')
        suppliers = []
        unsorted = []

    # Render template with data
    return render_template('stock/receuve_unsorted_stock.html', supplier_ids=suppliers, unsorted=unsorted)



#delivery route

@stock.route('/delivery', methods=['GET', 'POST'])
def delivery():
    if request.method == 'POST':
        # Retrieve and validate form data
        pole_status = request.form.get('pole_status')
        quantity = request.form.get('quantity')
        description = request.form.get('description')

        # Check for missing fields
        missing_fields = []
        if not pole_status:
            missing_fields.append('Pole Type')
        if not quantity:
            missing_fields.append('Quantity')
        if not description:
            missing_fields.append('Description')

        if missing_fields:
            flash(f'Missing fields: {", ".join(missing_fields)}', 'danger')
            return redirect(url_for('stock.delivery'))
        
        return render_template('stock/delivery.html')
    


# recieve clients stock

@stock.route('/receive_clients_stock', methods=['POST', 'GET'])
def receive_clients_stock():
    clients = []
    try:
        # Fetch clients
        try:
            result = supabase.table('clients').select('*').execute()
            clients = result.data if result else []
        except Exception as db_error:
            flash(f"Failed to load clients: {str(db_error)}", 'danger')

        if request.method == 'POST':
            # Debug: Print form data
            print("Form Data Received:", request.form)

            # Retrieve form data
            client_id = request.form.get('client_id')
            pole_type = request.form.get('pole_type')
            quantity = request.form.get('quantity')
            pole_size = None

            if pole_type != 'unsorted':
                pole_size = request.form.get('pole_size')

            # Validate the data
            error_messages = []
            if not client_id:
                error_messages.append('Client ID is required.')
            if not pole_type:
                error_messages.append('Pole type is required.')
            if not quantity or not quantity.isdigit() or int(quantity) <= 0:
                error_messages.append('Valid quantity (greater than 0) is required.')
            if pole_type != 'unsorted' and not pole_size:
                error_messages.append('Pole size is required for sorted poles.')

            # Handle validation errors
            if error_messages:
                for msg in error_messages:
                    flash(msg, 'danger')
                return render_template('Stock/recieveclientstock.html', clients=clients)

            # Insert into database
            clients_stock = {
                "client_id": client_id,
                "pole_type": pole_type,
                "pole_size": pole_size,
                "quantity": int(quantity),
                "date": datetime.utcnow().isoformat()
            }
            print("Prepared Data for Database:", clients_stock)

            response = supabase.table('clients_stock').insert(clients_stock).execute()
            if response.error:
                flash(f"Error saving client stock: {response.error['message']}", 'danger')
                return render_template('Stock/recieveclientstock.html', clients=clients)

            flash('Client stock successfully received!', 'success')
            return redirect(url_for('stock.clients_stock'))

        # GET request: Render the form
        return render_template('Stock/recieveclientstock.html', clients=clients)

    except Exception as e:
        flash(f"An unexpected error occurred: {str(e)}", 'danger')
        return render_template('Stock/recieveclientstock.html', clients=clients)


@stock.route('/clients_stock', methods=['GET', 'POST'])
def clients_stock():
    search_query = request.form.get('search_query', '').strip()
    clients = []
    client_stocks = []

    try:
        # Fetch clients and filter if a search query is provided
        if search_query:
            clients = (
                supabase.table('clients')
                .select("*")
                .ilike('name', f"%{search_query}%")
                .execute()
                .data
            )
        else:
            clients = supabase.table('clients').select("*").execute().data
            print(clients)

        # Get client IDs to fetch related stocks
        client_ids = [client['id'] for client in clients]
        if client_ids:
            client_stocks = (
                supabase.table('client_stock')
                .select("client_id, pole_type, pole_size, quantity, treatment_status")
                .in_("client_id", client_ids)
                .execute()
                .data
            )

    except Exception as e:
        flash(f"Error fetching data: {str(e)}", "danger")
        print(e)

    # Combine clients with their stocks
    clients_with_stock = []
    for client in clients:
        stock_items = [
            stock
            for stock in client_stocks
            if stock['client_id'] == client['id']
        ]
        clients_with_stock.append({
            "id": client["id"],
            "name": client["name"],
            "stock": stock_items,
        })

    return render_template(
        "stock/clients_stock.html",
        clients=clients_with_stock,
        search_query=search_query,
    )

    
@stock.route('/sort_stock', methods=['GET', 'POST'])
def sort_stock():
    if request.method == 'POST':
        stock_id = request.form.get('stock_id')
        if not stock_id:
            flash('Stock ID is required', 'danger')
            return redirect(url_for('stock.sort_stock'))
            
        category = request.form.get('category')
        size = request.form.get('size')
        is_reject = request.form.get('is_reject') == 'true'
        supplier_id = request.form.get('supplier_id')

        try:
            # First, get the unsorted stock item
            unsorted_item = supabase.table('unsorted_stock').select('*').eq('id', stock_id).single().execute()
            
            if not unsorted_item.data:
                flash('Stock item not found', 'danger')
                return redirect(url_for('stock.sort_stock'))
            # Prepare data for sorted stock or rejects
            sorted_data = {
                'date': datetime.utcnow().isoformat(),
                "rafters": unsorted_item.data.get('rafters'),
                "timber": unsorted_item.data.get('timber'),
                "fencing_poles": unsorted_item.data.get('fencing_poles'),
                "telecom_poles": unsorted_item.data.get('telecom_poles'),
                "7m": unsorted_item.data.get('7m'),
                "8m": unsorted_item.data.get('8m'),
                "9m": unsorted_item.data.get('9m'),
                "10m": unsorted_item.data.get('10m'),
                "11m": unsorted_item.data.get('11m'),
                "12m": unsorted_item.data.get('12m'),
                "14m": unsorted_item.data.get('14m'),
                "16m": unsorted_item.data.get('16m'),
                'supplier_id': supplier_id
            }
            print(sorted_data)

            if is_reject:
                # Move to rejects table
                sorted_data['reason'] = request.form.get('reject_reason')
                supabase.table('rejects').insert(sorted_data).execute()
            else:
                # Move to sorted stock based on category
                if category in ['rafters', 'timber', 'fencing_poles']:
                    sorted_data['category'] = category
                    supabase.table('sorted_stock').insert(sorted_data).execute()
                
                elif category == 'telecom_poles':
                    if size in ['7m', '8m', '9m']:
                        sorted_data['size'] = size
                        sorted_data['category'] = 'telecom'
                        supabase.table('sorted_stock').insert(sorted_data).execute()
                
                elif category == 'electricity_poles':
                    if size in ['9m', '10m', '11m', '12m', '14m', '16m']:
                        sorted_data['size'] = size
                        sorted_data['category'] = 'electricity'
                        supabase.table('sorted_stock').insert(sorted_data).execute()

            # Delete from unsorted stock
            supabase.table('unsorted_stock').delete().eq('id', stock_id).execute()
        except Exception as e:
            error_details = getattr(e, 'error', str(e))
            flash(f'Error sorting stock: {error_details}', 'danger')
            print(f"Full error details: {error_details}")
        except Exception as e:
            flash(f'Error sorting stock: {str(e)}', 'danger')
            print(e)
            
        return redirect(url_for('stock.sort_stock'))

    # GET request - fetch unsorted stock
    try:
        unsorted_stock = supabase.table('unsorted_stock').select('*').execute().data
        suppliers = supabase.table('suppliers').select('*').execute().data
    except Exception as e:
        flash(f'Error fetching data: {str(e)}', 'danger')
        print(e)
        unsorted_stock = []
        print(unsorted_stock)
        suppliers = []
        print(suppliers)


    return render_template('stock/sort_stock.html', unsorted_stock=unsorted_stock, suppliers=suppliers)