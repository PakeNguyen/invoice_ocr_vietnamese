# ===== IMPORT =====
import torch
import re
import cv2
import pandas as pd
from PIL import Image
from paddleocr import PaddleOCR
from vietocr.tool.config import Cfg
from vietocr.tool.predictor import Predictor

# ===== CONFIG =====
DEVICE = 'cuda' if torch.cuda.is_available() else 'cpu'
VIETOCR_MODEL_PATH = r'C:\Users\Admin\AppData\Local\Temp\vgg_transformer.pth'


# ===== PADDLEOCR =====
def init_paddleocr():
    """Khởi tạo mô hình PaddleOCR tiếng Việt có xoay góc"""
    return PaddleOCR(use_angle_cls=True, lang='vi')

def run_paddleocr(image_path, ocr_model):
    """Chạy PaddleOCR và trả về kết quả + ảnh RGB"""
    image = cv2.imread(image_path)
    image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    result = ocr_model.ocr(image_rgb, cls=True)
    return result, image_rgb


# ===== VIETOCR =====
def init_vietocr(model_path, device='cpu'):
    """Khởi tạo mô hình VietOCR với cấu hình vgg_transformer"""
    config = Cfg.load_config_from_name('vgg_transformer')
    config['weights'] = model_path
    config['device'] = device
    return Predictor(config)

def vietocr_predict(predictor, cropped_img):
    """Nhận diện văn bản từ ảnh nhỏ bằng VietOCR"""
    pil_img = Image.fromarray(cropped_img)
    return predictor.predict(pil_img)


# ===== OCR KẾT HỢP =====
def combine_ocr(image_rgb, result_paddle, vietocr_predictor):
    """Dùng Paddle để detect box → dùng VietOCR để nhận diện text"""
    data = []
    for line in result_paddle[0]:
        box, (text, conf) = line
        x1 = int(min([pt[0] for pt in box]))
        y1 = int(min([pt[1] for pt in box]))
        x2 = int(max([pt[0] for pt in box]))
        y2 = int(max([pt[1] for pt in box]))
        cropped = image_rgb[y1:y2, x1:x2]
        try:
            text_vietocr = vietocr_predict(vietocr_predictor, cropped)
        except:
            text_vietocr = ""
        data.append({
            'x1': x1, 'y1': y1, 'x2': x2, 'y2': y2,
            'text_paddle': text,
            'conf_paddle': conf,
            'text_vietocr': text_vietocr
        })
    return pd.DataFrame(data)


# ===== GOM DÒNG =====
def group_boxes_to_lines(df, line_threshold=30):
    df_sorted = df.sort_values(by='y1').reset_index(drop=True)
    lines, cur_line, last_y = [], [], -1000

    for _, row in df_sorted.iterrows():
        y_center = (row['y1'] + row['y2']) / 2
        if abs(y_center - last_y) > line_threshold:
            if cur_line:
                lines.append(cur_line)
            cur_line = [row]
            last_y = y_center
        else:
            cur_line.append(row)
    if cur_line:
        lines.append(cur_line)

    # Ghép text + lấy bbox dòng (min x1, min y1, max x2, max y2)
    line_results = []
    for line in lines:
        line_text = ' '.join([r['text_vietocr'] for r in sorted(line, key=lambda r: r['x1'])])
        x1 = min(r['x1'] for r in line)
        y1 = min(r['y1'] for r in line)
        x2 = max(r['x2'] for r in line)
        y2 = max(r['y2'] for r in line)
        line_results.append({'line_text': line_text, 'bbox': [x1, y1, x2, y2]})

    return pd.DataFrame(line_results)



# ===== TRÍCH THÔNG TIN =====
def extract_invoice_info(df_lines):
    """Trích xuất thông tin chi tiết từ hóa đơn OCR đầu vào (df_lines)"""
    invoice_info = {}

    # 1. Tên quán: thường nằm ở dòng đầu tiên
    invoice_info['restaurant_name'] = df_lines.iloc[0]['line_text'].strip()

    # 2. Số điện thoại
    phone_line = df_lines[df_lines['line_text'].str.contains(r'(\d{9,11})', regex=True)]
    if not phone_line.empty:
        match = re.search(r'\d{9,11}', phone_line.iloc[0]['line_text'])
        if match:
            invoice_info['phone'] = match.group()

    # 3. Địa chỉ
    address = ''
    address_idx = -1
    for idx, row in df_lines.iterrows():
        text = row['line_text'].lower()
        if 'đc:' in text or 'địa chỉ' in text:
            address = row['line_text'].strip()
            address_idx = idx
            break

    if address_idx != -1:
        y_bottom = df_lines.iloc[address_idx]['bbox'][3]
        for i in range(address_idx + 1, len(df_lines)):
            next_line = df_lines.iloc[i]
            y_top = next_line['bbox'][1]
            next_text = next_line['line_text'].strip()
            # Nếu dòng tiếp theo gần về vị trí và không chứa từ khóa kết thúc thì nối vào
            if abs(y_top - y_bottom) < 30 and not re.search(r'(phiếu|tổng|thu ngân|bàn|món|tiền|ngày)', next_text, re.IGNORECASE):
                address += ' ' + next_text
                y_bottom = next_line['bbox'][3]  # cập nhật tọa độ
            else:
                break
        invoice_info['address'] = address.strip()

    # 4. Số phiếu hóa đơn
    bill_line = df_lines[df_lines['line_text'].str.contains(r'Phiếu[:\d]', case=False)]
    if not bill_line.empty:
        match = re.search(r'Phiếu[:\s]*([A-Z0-9]+)', bill_line.iloc[0]['line_text'], re.IGNORECASE)
        if match:
            invoice_info['bill_id'] = match.group(1)

    # 5. Ngày
    date_line = df_lines[df_lines['line_text'].str.contains(r'\d{4}-\d{2}-\d{2}')]
    if not date_line.empty:
        date_match = re.search(r'\d{4}-\d{2}-\d{2}', date_line.iloc[0]['line_text'])
        if date_match:
            invoice_info['date'] = date_match.group()

    # 6. Bàn
    table_line = df_lines[df_lines['line_text'].str.contains(r'Bàn', case=False)]
    if not table_line.empty:
        match = re.search(r'Bàn[:\s]*([A-Z0-9]+)', table_line.iloc[0]['line_text'], re.IGNORECASE)
        if match:
            invoice_info['table'] = match.group(1)

    # 7. Nhân viên
    nv_line = df_lines[df_lines['line_text'].str.contains(r'Nhân viên', case=False)]
    if not nv_line.empty:
        match = re.search(r'Nhân viên[:\s]*(.+)', nv_line.iloc[0]['line_text'], re.IGNORECASE)
        if match:
            invoice_info['staff'] = match.group(1).strip()

    # 8. Thu ngân
    cashier_line = df_lines[df_lines['line_text'].str.contains(r'Thu ngân', case=False)]
    if not cashier_line.empty:
        match = re.search(r'Thu ngân[:\s]*(.+)', cashier_line.iloc[0]['line_text'], re.IGNORECASE)
        if match:
            invoice_info['cashier'] = match.group(1).strip()

    # 9. Danh sách món ăn (menu)
    try:
        start_idx = df_lines[df_lines['line_text'].str.contains(r'(Đơn giá|SL)', case=False)].index[0]
        end_idx = df_lines[df_lines['line_text'].str.contains(r'(Tổng cộng|Tiền mặt)', case=False)].index[0]
        menu_lines = df_lines.loc[start_idx+1:end_idx, 'line_text'].tolist()

        menu_items = []
        pattern = re.compile(r'''
            ^\s*
            (?P<name>.+?)                                # Tên món
            \s+
            (?P<qty>\d+)                                 # Số lượng
            \s+
            (?P<unit>\d{1,3}(?:[.,]\d{3})+)              # Đơn giá
            \s+
            (?P<total>\d{1,3}(?:[.,]\d{3})+)             # Thành tiền
            \s*$
        ''', re.VERBOSE)

        for line in menu_lines:
            m = pattern.match(line)
            if m:
                name = m.group('name').strip()
                qty = int(m.group('qty'))
                unit = int(m.group('unit').replace('.', '').replace(',', ''))
                total = int(m.group('total').replace('.', '').replace(',', ''))
                menu_items.append({
                    'name': name,
                    'qty': qty,
                    'unit_price': unit,
                    'total': total
                })

        invoice_info['menu'] = menu_items
    except Exception as e:
        invoice_info['menu'] = []
        print(f"[!] Lỗi khi trích xuất menu: {e}")

    # 10. Tổng cộng
    total_line = df_lines[df_lines['line_text'].str.contains(r'Tổng cộng', case=False)]
    if not total_line.empty:
        match = re.search(r'(\d{1,3}(?:[.,]\d{3})+)', total_line.iloc[0]['line_text'])
        if match:
            invoice_info['total_amount'] = int(match.group(1).replace('.', '').replace(',', ''))

    # 11. Hình thức thanh toán
    pay_line = df_lines[df_lines['line_text'].str.contains(r'Tiền mặt|Chuyển khoản', case=False)]
    if not pay_line.empty:
        text = pay_line.iloc[0]['line_text'].lower()
        if 'tiền mặt' in text:
            invoice_info['payment_method'] = 'Tiền mặt'
        elif 'chuyển khoản' in text:
            invoice_info['payment_method'] = 'Chuyển khoản'

    return invoice_info


# ===== MAIN =====
def main(image_path):
    """Pipeline chính"""
    print(f"[INFO] Đang xử lý: {image_path}")
    
    # 1. Khởi tạo mô hình
    paddleocr_model = init_paddleocr()
    vietocr_model = init_vietocr(VIETOCR_MODEL_PATH, DEVICE)

    # 2. OCR
    result_paddle, image_rgb = run_paddleocr(image_path, paddleocr_model)
    df_ocr = combine_ocr(image_rgb, result_paddle, vietocr_model)

    # 3. Gom dòng
    df_lines = group_boxes_to_lines(df_ocr)

    # 4. Trích xuất thông tin
    info = extract_invoice_info(df_lines)

    print("\n==== Thông tin hóa đơn ====")
    print(info)
    print("\n==== Các dòng OCR ====")
    print(df_lines)

    df_lines.to_csv('ocr_lines.csv', index=False, encoding='utf-8-sig')
    return info, df_lines


# ===== CHẠY THỬ =====
if __name__ == "__main__":
    image_path = 'HD3.jpg'  # đường dẫn ảnh
    main(image_path)
