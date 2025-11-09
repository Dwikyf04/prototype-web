import os
from datetime import datetime
import io

from pyparsing import wraps
import cloudinary
import cloudinary.uploader

from reportlab.pdfgen import canvas
from flask import Flask, render_template, request, redirect, url_for, flash, send_file, session
from flask_mail import Mail, Message
from flask_sqlalchemy import SQLAlchemy   
from config import Config

app = Flask(__name__)
app.config.from_object(Config)

db = SQLAlchemy(app)
mail = Mail(app)
cloudinary.config(
    cloud_name=app.config['CLOUD_NAME'],
    api_key=app.config['CLOUDINARY_API_KEY'],
    api_secret=app.config['CLOUDINARY_API_SECRET'],
    secure=True
)

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    school_name = db.Column(db.String(150), nullable=False)
    contact_person = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(150), nullable=False)
    phone = db.Column(db.String(40), nullable=True)
    product = db.Column(db.String(150), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    total_price = db.Column(db.Numeric(14,2), nullable=True)
    payment_proof_url = db.Column(db.String(500), nullable=True)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
 
def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('admin_logged_in'):
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated

def generate_order_pdf_bytes(order: Order):
    """Generate PDF bytes (reportlab) for an order."""
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=(595, 842))  # A4-ish px
    p.setFont("Helvetica-Bold", 14)
    p.drawString(50, 800, "CV. Sejahtera - Notulensi Pemesanan")
    p.setFont("Helvetica", 11)
    p.drawString(50, 780, f"Tanggal: {order.created_at.strftime('%d-%m-%Y %H:%M:%S')}")
    p.drawString(50, 760, f"Sekolah: {order.school_name}")
    p.drawString(50, 740, f"Kontak person: {order.contact_person} | Email: {order.email} | Telp: {order.phone or '-'}")
    p.drawString(50, 720, f"Produk: {order.product}")
    p.drawString(50, 700, f"Jumlah: {order.quantity}")
    if order.total_price:
        p.drawString(50, 680, f"Total Harga: Rp {int(order.total_price):,}")
    p.drawString(50, 660, "Keterangan:")
    text = p.beginText(50, 640)
    text.setFont("Helvetica", 10)
    notes = (order.notes or "").strip()
    if notes == "":
        notes = "-"
    for line in notes.splitlines():
        text.textLine(line)
    p.drawText(text)
    p.drawString(50, 580, f"Bukti Pembayaran (URL):")
    p.setFillColorRGB(0,0,1)
    p.drawString(50, 560, order.payment_proof_url or "-")
    p.setFillColorRGB(0,0,0)
    p.showPage()
    p.save()
    buffer.seek(0)
    return buffer

# --- Routes ---
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/catalog')
def catalog():
    # static product list for now; later move to DB if needed
    products = [
        {"id": 1, "name": "Laptop", "price": 7500000},
        {"id": 2, "name": "Kursi", "price": 500000},
        {"id": 3, "name": "Komputer", "price": 8500000},
        {"id": 4, "name": "Proyektor", "price": 4500000},
        {"id": 5, "name": "Papan Tulis", "price": 800000}
    ]
    return render_template('catalog.html', products=products)

@app.route('/order', methods=['GET', 'POST'])
def order():
    if request.method == 'POST':
        # get form
        school_name = request.form.get('school_name')
        contact_person = request.form.get('contact_person')
        email = request.form.get('email')
        phone = request.form.get('phone')
        product = request.form.get('product')
        quantity = int(request.form.get('quantity', 1))
        price = float(request.form.get('price', 0) or 0)
        total_price = price * quantity
        notes = request.form.get('notes')

        # upload file to Cloudinary
        file = request.files.get('payment_proof')
        proof_url = None
        if file and file.filename != '':
            res = cloudinary.uploader.upload(file, folder="cv_sejahtera/payments")
            proof_url = res.get('secure_url')

        # save to DB
        order = Order(
            school_name=school_name,
            contact_person=contact_person,
            email=email,
            phone=phone,
            product=product,
            quantity=quantity,
            total_price=total_price,
            payment_proof_url=proof_url,
            notes=notes
        )
        db.session.add(order)
        db.session.commit()

        # generate PDF bytes
        pdf_buf = generate_order_pdf_bytes(order)

        # send email to admin with PDF attachment
        admin_email = app.config.get('ADMIN_EMAIL')
        msg = Message(subject=f"[CV.Sejahtera] Pesanan Baru dari {school_name}",
                      sender=app.config.get('MAIL_DEFAULT_SENDER'),
                      recipients=[admin_email])
        body = f"""
Pesanan baru masuk:
Sekolah: {school_name}
Kontak: {contact_person}
Email: {email}
Produk: {product}
Jumlah: {quantity}
Total: Rp {int(total_price):,}
Bukti pembayaran: {proof_url or '-'}
Waktu: {order.created_at.strftime('%d-%m-%Y %H:%M:%S')}
"""
        msg.body = body
        # attach PDF
        msg.attach(f"notulensi_order_{order.id}.pdf", "application/pdf", pdf_buf.getvalue())
        try:
            mail.send(msg)
        except Exception as e:
            # don't fail the user; log server console
            print("Failed to send email:", e)

        return redirect(url_for('success', order_id=order.id))
    # GET
    product_name = request.args.get('product', '')
    price = request.args.get('price', '')
    return render_template('order.html', product_name=product_name, price=price)

@app.route('/success/<int:order_id>')
def success(order_id):
    order = Order.query.get_or_404(order_id)
    return render_template('success.html', order=order)

@app.route('/download_pdf/<int:order_id>')
def download_pdf(order_id):
    order = Order.query.get_or_404(order_id)
    pdf_buf = generate_order_pdf_bytes(order)
    return send_file(pdf_buf, as_attachment=True, download_name=f"notulensi_order_{order.id}.pdf", mimetype="application/pdf")

# --- Admin auth & dashboard ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        u = request.form.get('username')
        p = request.form.get('password')
        if u == app.config.get('ADMIN_USER') and p == app.config.get('ADMIN_PASS'):
            session['admin_logged_in'] = True
            return redirect(url_for('admin'))
        else:
            flash('Username atau password salah', 'danger')
            return redirect(url_for('login'))
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/admin')
@admin_required
def admin():
    orders = Order.query.order_by(Order.created_at.desc()).all()
    return render_template('admin.html', orders=orders)

# --- Startup ---
if __name__ == "__main__":
    # create DB tables if not exist
    with app.app_context():
        db.create_all()
    app.run(host='0.0.0.0', port=int(os.getenv("PORT", 5000)))
 