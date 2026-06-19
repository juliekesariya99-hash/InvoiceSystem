from django.http import HttpResponse
from reportlab.pdfgen import canvas
from .models import Invoice
from django.shortcuts import render
from .models import Customer, Product, Invoice, InvoiceItem
import qrcode
import tempfile
from reportlab.lib.utils import ImageReader

def create_invoice(request):
    customers = Customer.objects.all()
    products = Product.objects.all()
    invoices = Invoice.objects.all().order_by('-date')

    if request.method == "POST":
        customer_id = request.POST.get("customer")
        product_id = request.POST.get("product")
        quantity = int(request.POST.get("quantity"))

        customer = Customer.objects.get(id=customer_id)
        product = Product.objects.get(id=product_id)

        # Calculate item total
        item_total = product.price * quantity

        # Create new invoice
        invoice = Invoice.objects.create(customer=customer, total_amount=item_total)

        # Create invoice item
        InvoiceItem.objects.create(
            invoice=invoice,
            product=product,
            quantity=quantity,
            price=product.price
        )

    return render(request, "billing/create_invoice.html", {
        "customers": customers,
        "products": products,
        "invoices": invoices
    })


def invoice_detail(request, pk):
    invoice = Invoice.objects.get(id=pk)
    items = InvoiceItem.objects.filter(invoice=invoice)
    
    # Add calculated total for each item
    for item in items:
        item.line_total = item.price * item.quantity
    
    return render(request, "billing/invoice_detail.html", {
        "invoice": invoice,
        "items": items
    })


def download_invoice_pdf(request, pk):
    invoice = Invoice.objects.get(id=pk)
    items = InvoiceItem.objects.filter(invoice=invoice)
    
    # Add calculated total for each item
    for item in items:
        item.line_total = item.price * item.quantity

    # Create QR Data
    qr_data = f"""
Invoice ID: {invoice.id}
Customer: {invoice.customer.name}
Date: {invoice.date.strftime('%B %d, %Y')}
Total: ₹{invoice.total_amount}
"""

    # Generate QR Image
    qr = qrcode.make(qr_data)
    
    temp = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
    temp_path = temp.name
    temp.close()  # Close the file handle so it can be read
    qr.save(temp_path)

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="invoice_{invoice.id}.pdf"'

    p = canvas.Canvas(response)

    # Title
    p.setFont("Helvetica-Bold", 16)
    p.drawString(250, 800, "INVOICE")

    # Invoice Details
    p.setFont("Helvetica", 11)
    p.drawString(50, 750, f"Invoice #: {invoice.id}")
    p.drawString(50, 730, f"Customer: {invoice.customer.name}")
    p.drawString(50, 710, f"Date: {invoice.date.strftime('%B %d, %Y')}")

    # Table Header
    p.setFont("Helvetica-Bold", 10)
    p.drawString(50, 670, "Product")
    p.drawString(200, 670, "Price")
    p.drawString(300, 670, "Qty")
    p.drawString(380, 670, "Total")

    # Table Line
    p.line(50, 660, 500, 660)

    # Items
    p.setFont("Helvetica", 10)
    y = 640
    for item in items:
        p.drawString(50, y, item.product.name[:25])
        p.drawString(200, y, f"₹{item.price}")
        p.drawString(300, y, str(item.quantity))
        p.drawString(380, y, f"₹{item.line_total}")
        y -= 20

    # Total Line
    p.line(50, y - 10, 500, y - 10)
    
    # Grand Total
    p.setFont("Helvetica-Bold", 11)
    p.drawString(300, y - 30, "Total Amount:")
    p.drawString(380, y - 30, f"₹{invoice.total_amount}")

    # Add QR Code to PDF (positioned above bottom with good spacing)
    p.drawImage(
        ImageReader(temp_path),
        50,
        350,
        width=100,
        height=100
    )

    p.showPage()
    p.save()

    return response


def dashboard(request):
    total_customers = Customer.objects.count()
    total_products = Product.objects.count()
    total_invoices = Invoice.objects.count()

    total_revenue = 0
    invoices = Invoice.objects.all()

    for inv in invoices:
        total_revenue += inv.total_amount

    return render(request, "billing/dashboard.html", {
        "total_customers": total_customers,
        "total_products": total_products,
        "total_invoices": total_invoices,
        "total_revenue": total_revenue
    })