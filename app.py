from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import re
import os

app = Flask(__name__)

# Configuración de PostgreSQL en Render
DATABASE_URL = os.environ.get('DATABASE_URL', 'postgresql://cotizacion_db_user:X8Z2sC1M4zZjI3HRKR1sp46OWVhirUID@dpg-cudb6g0gph6c73b7mug0-a.oregon-postgres.render.com/cotizacion_db')
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
app.config['SECRET_KEY'] = 'MiyagiBestOsito'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Modelos
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    lastname = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    date = db.Column(db.String(10), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user = db.relationship('User', backref=db.backref('products', lazy=True))

@app.route('/')
def home():
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        lastname = request.form['lastname']
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        
        if password != confirm_password:
            flash("Las contraseñas no coinciden")
            return render_template('register.html')
        
        try:
            new_user = User(
                name=name,
                lastname=lastname,
                email=email,
                password=password
            )
            db.session.add(new_user)
            db.session.commit()
            return redirect(url_for('login'))
        except:
            flash("Error al registrar usuario")
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        user = User.query.filter_by(email=email, password=password).first()
        
        if user:
            session['user_id'] = user.id
            session['name'] = user.name
            return redirect(url_for('dashboard'))
        else:
            flash("Email o contraseña incorrectos")
    
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    if 'temp_products' not in session:
        session['temp_products'] = []
    
    temp_products = session.get('temp_products', [])
    total = sum(float(product['amount']) for product in temp_products)
    
    return render_template('dashboard.html', products=temp_products, total=total)

@app.route('/add_product', methods=['POST'])
def add_product():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    product_name = request.form.get('product_name')
    amount = request.form.get('amount')
    date = request.form.get('date')
    
    if all([product_name, amount, date]):
        if 'temp_products' not in session:
            session['temp_products'] = []
        
        # Convertir la fecha al formato correcto
        date_obj = datetime.strptime(date, '%Y-%m-%d')
        formatted_date = date_obj.strftime('%d/%m/%Y')
        
        session['temp_products'].append({
            'name': product_name,
            'amount': amount,
            'date': formatted_date
        })
        
        # Guardar la fecha en la sesión
        session['current_date'] = date  # Guardamos el formato original
        session.modified = True
    
    return redirect(url_for('dashboard'))

@app.route('/save_products', methods=['POST'])
def save_products():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    if 'temp_products' in session and session['temp_products']:
        try:
            for product in session['temp_products']:
                new_product = Product(
                    name=product['name'],
                    amount=float(product['amount']),
                    date=product['date'],
                    user_id=session['user_id']
                )
                db.session.add(new_product)
            
            db.session.commit()
            session['temp_products'] = []
            session.modified = True
            flash('Productos guardados exitosamente', 'success')
        except Exception as e:
            db.session.rollback()
            flash('Error al guardar los productos', 'error')
    
    return redirect(url_for('dashboard'))

@app.route('/update_products', methods=['POST'])
def update_products():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    try:
        # Obtener los datos del formulario
        product_names = request.form.getlist('product_name[]')
        product_amounts = request.form.getlist('product_amount[]')
        edit_date = request.form.get('edit_date')
        
        # Eliminar todos los productos existentes de esa fecha
        Product.query.filter_by(
            user_id=session['user_id'],
            date=edit_date
        ).delete()
        
        # Agregar solo los productos que no fueron eliminados
        for name, amount in zip(product_names, product_amounts):
            if name.strip():  # Solo si el nombre no está vacío
                new_product = Product(
                    name=name,
                    amount=float(amount),
                    date=edit_date,
                    user_id=session['user_id']
                )
                db.session.add(new_product)
        
        db.session.commit()
        flash('Cambios guardados exitosamente')
        
        # Redirigir a la búsqueda con la misma fecha
        return redirect(url_for('table_page'))
        
    except Exception as e:
        print(f"Error al actualizar productos: {str(e)}")
        db.session.rollback()
        flash('Error al guardar los cambios')
        return redirect(url_for('table_page'))
    
@app.route('/table')
def table():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    try:
        # Obtener productos guardados del usuario actual
        products = Product.query.filter_by(user_id=session['user_id']).all()
        
        # Convertir productos a formato para mostrar
        product_list = []
        for product in products:
            product_list.append({
                'id': product.id,
                'name': product.name,
                'amount': product.amount,
                'date': product.date
            })
        
        # Calcular total
        total = sum(float(product['amount']) for product in product_list)
        
        return render_template('table.html', 
                             products=product_list, 
                             total=total)
    except Exception as e:
        print(f"Error en tabla: {str(e)}")  # Para debugging
        flash('Error al cargar los productos')
        return redirect(url_for('dashboard'))

@app.route('/import')
def import_page():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    # Obtener la fecha de la sesión si existe
    current_date = session.get('current_date')
    if current_date:
        try:
            # Convertir la fecha al formato correcto
            date_obj = datetime.strptime(current_date, '%Y-%m-%d')
            formatted_date = date_obj.strftime('%d/%m/%Y')
            
            # Buscar productos por fecha
            products = Product.query.filter_by(
                user_id=session['user_id'],
                date=formatted_date
            ).all()
            
            if products:
                saved_products = [{
                    'name': product.name,
                    'amount': product.amount,
                    'date': product.date
                } for product in products]
                
                total = sum(float(product['amount']) for product in saved_products)
                
                return render_template('import.html', 
                                     saved_products=saved_products, 
                                     total=total,
                                     search_date=formatted_date)
        except Exception as e:
            print(f"Error al cargar productos: {str(e)}")
    
    return render_template('import.html')

@app.route('/clear_temp_table', methods=['POST'])
def clear_temp_table():
    if 'user_id' not in session:
        return '', 401
    
    session['temp_products'] = []
    session.modified = True
    return '', 200

@app.route('/delete_temp_product/<int:index>', methods=['POST'])
def delete_temp_product(index):
    if 'user_id' not in session:
        return '', 401
    
    if 'temp_products' in session:
        try:
            session['temp_products'].pop(index)
            session.modified = True
            return '', 200
        except IndexError:
            return '', 404
    
    return '', 404


@app.route('/search_by_date', methods=['POST'])
def search_by_date():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    search_date = request.form.get('search_date')
    
    if search_date:
        try:
            # Convertir la fecha al formato correcto para la búsqueda
            date_obj = datetime.strptime(search_date, '%Y-%m-%d')
            formatted_date = date_obj.strftime('%d/%m/%Y')
            
            # Buscar productos por fecha
            products = Product.query.filter_by(
                user_id=session['user_id'],
                date=formatted_date
            ).all()
            
            if products:
                saved_products = [{
                    'id': product.id,
                    'name': product.name,
                    'amount': product.amount,
                    'date': product.date
                } for product in products]
                
                total = sum(float(product['amount']) for product in saved_products)
                
                return render_template('import.html', 
                                     saved_products=saved_products, 
                                     total=total,
                                     search_date=formatted_date)
            else:
                flash(f'No se encontraron productos para la fecha {formatted_date}')
        except Exception as e:
            flash('Error al buscar productos')
    
    return redirect(url_for('table_page'))

@app.route('/table_page')
def table_page():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('table.html')

@app.route('/save_current_date', methods=['POST'])
def save_current_date():
    if 'user_id' not in session:
        return '', 401
    
    data = request.get_json()
    if data and 'date' in data:
        try:
            # Convertir la fecha al formato dd/mm/yyyy
            date_obj = datetime.strptime(data['date'], '%Y-%m-%d')
            formatted_date = date_obj.strftime('%d/%m/%Y')
            session['current_date'] = formatted_date
            session.modified = True
        except:
            session['current_date'] = data['date']
            session.modified = True
    
    return '', 200

@app.route('/save_changes', methods=['POST'])
def save_changes():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    try:
        # Obtener los datos del formulario
        names = request.form.getlist('name[]')
        amounts = request.form.getlist('amount[]')
        date = request.form.get('date')
        
        # Obtener productos existentes
        existing_products = Product.query.filter_by(
            user_id=session['user_id'],
            date=date
        ).all()
        
        # Actualizar productos existentes
        for i, product in enumerate(existing_products):
            if i < len(names):
                product.name = names[i]
                product.amount = float(amounts[i])
        
        db.session.commit()
        flash('Productos actualizados exitosamente', 'success')
    except Exception as e:
        print(f"Error al actualizar: {str(e)}")
        db.session.rollback()
        flash('Error al actualizar los productos', 'error')
    
    return redirect(url_for('search_by_date'), code=307)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)