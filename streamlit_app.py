import streamlit as st
import mysql.connector
from PIL import Image
import tempfile

from invoice_ocr_app import main  # Gọi hàm OCR

import warnings
warnings.filterwarnings("ignore")

# ==== CẤU HÌNH GIAO DIỆN STREAMLIT ====
st.set_page_config(page_title="OCR Hóa đơn", layout="wide")

# ==== MỞ RỘNG CHIỀU NGANG TOÀN BỘ TRÊN STREAMLIT NẾU KHÔNG CÓ ĐOẠN NÀY SẼ CÓ ÍT KHÔNG GIAN HIỂN THỊ THÔNG TIN LÊN GIAO DIỆN ====
st.markdown("""
    <style>
        .main .block-container {
            padding-left: 1rem;
            padding-right: 1rem;
            max-width: 100% !important;
        }
    </style>
""", unsafe_allow_html=True)

st.title("📄 Trích xuất thông tin hóa đơn (OCR + VietOCR)")

# ==== KẾT NỐI DATABASE ====
def get_db_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="1632002",
        database="invoice_db"
    )

def save_to_database(info):
    conn = get_db_connection()
    cursor = conn.cursor()

    insert_invoice = """
    INSERT INTO invoices (bill_id, cashier, date, payment_method, phone, restaurant_name, address, staff, table_id, total_amount)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
    invoice_data = (
        info.get("bill_id", ""),
        info.get("cashier", ""),
        info.get("date", ""),
        info.get("payment_method", ""),
        info.get("phone", ""),
        info.get("restaurant_name", ""),
        info.get("address", ""),
        info.get("staff", ""),
        info.get("table", ""),
        info.get("total_amount", 0)
    )
    cursor.execute(insert_invoice, invoice_data)
    invoice_id = cursor.lastrowid

    for item in info["menu"]:
        insert_item = """
        INSERT INTO invoice_items (invoice_id, name, qty, unit_price, total)
        VALUES (%s, %s, %s, %s, %s)
        """
        item_data = (
            invoice_id,
            item["name"],
            item["qty"],
            item["unit_price"],
            item["total"]
        )
        cursor.execute(insert_item, item_data)

    conn.commit()
    cursor.close()
    conn.close()

# ==== GIAO DIỆN NGƯỜI DÙNG ====
uploaded_file = st.file_uploader("Tải ảnh hóa đơn", type=["jpg", "jpeg", "png"])

if uploaded_file:
    img = Image.open(uploaded_file)

    with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as temp_file:
        img.save(temp_file.name)
        image_path = temp_file.name

    with st.spinner("🔍 Đang xử lý ảnh OCR..."):
        info, _ = main(image_path)


    # ==== CHIA 2 PHẦN: ẢNH BÊN TRÁI, THÔNG TIN BÊN PHẢI ====
    left_col, right_col = st.columns([1.2, 2.2])
    with left_col:
        st.markdown("<h3 style='text-align: center;'>🖼️ Ảnh hóa đơn</h3>", unsafe_allow_html=True)
        st.image(img, caption="Ảnh hóa đơn", use_container_width=True)


    with right_col:
        st.markdown("<h3 style='text-align: center;'>📋 Thông tin hóa đơn</h3>", unsafe_allow_html=True)
        col1, col2 = st.columns(2)

        with col1:
            bill_id = st.text_input("🧾 Mã hóa đơn", info.get("bill_id", ""))
            restaurant_name = st.text_input("🍽️ Tên quán", info.get("restaurant_name", ""))
            phone = st.text_input("📱 Số điện thoại", info.get("phone", ""))
            cashier = st.text_input("👩‍💼 Thu ngân", info.get("cashier", ""))
            payment_method = st.text_input("💳 Phương thức thanh toán", info.get("payment_method", ""))

        with col2:
            date = st.date_input("📅 Ngày", info.get("date", "2024-01-01"))
            address = st.text_input("📍 Địa chỉ", info.get("address", ""))
            staff = st.text_input("👨‍🍳 Nhân viên phục vụ", info.get("staff", ""))
            table = st.text_input("🪑 Bàn số", info.get("table", ""))
            total_amount = st.number_input("💰 Tổng tiền", value=info.get("total_amount", 0), min_value=0)

        # ==== DANH SÁCH MÓN ĂN CHIA 2 CỘT ====
        st.subheader("📋 Danh sách món ăn")
        menu_items = []

        for i, item in enumerate(info.get("menu", [])):
            st.markdown(f"#### 🍽️ Món {i+1}")
            menu_col1, menu_col2 = st.columns(2)

            with menu_col1:
                name = st.text_input(f"Tên món {i+1}", item.get("name", ""), key=f"name_{i}")
                qty = st.number_input(f"Số lượng {i+1}", value=item.get("qty", 1), min_value=1, key=f"qty_{i}")

            with menu_col2:
                unit_price = st.number_input(f"Đơn giá {i+1}", value=item.get("unit_price", 0), min_value=0, key=f"price_{i}")
                total = st.number_input(f"Thành tiền {i+1}", value=item.get("total", 0), min_value=0, key=f"total_{i}")

            menu_items.append({
                "name": name,
                "qty": qty,
                "unit_price": unit_price,
                "total": total
            })

        # Tạo button vào để lưu database 
        if st.button("💾 Lưu vào cơ sở dữ liệu"):
            edited_info = {
                "bill_id": bill_id,
                "payment_method": payment_method,
                "restaurant_name": restaurant_name,
                "staff": staff,
                "total_amount": total_amount,
                "cashier": cashier,
                "date": date,
                "phone": phone,
                "address": address,
                "table": table,
                "menu": menu_items
            }
            save_to_database(edited_info)
            st.success("✅ Đã lưu thông tin vào cơ sở dữ liệu thành công!")

