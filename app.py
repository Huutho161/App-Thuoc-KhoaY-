import streamlit as st
import pandas as pd
import os
import base64
from datetime import datetime, timedelta
import qrcode
from io import BytesIO
from PIL import Image
from streamlit_gsheets import GSheetsConnection 

# ==========================================
# 1. CẤU HÌNH HỆ THỐNG & GIAO DIỆN
# ==========================================
st.set_page_config(page_title="Hệ thống Quản lý Đoàn - Hội Y NTTU", layout="wide", page_icon="🏥", initial_sidebar_state="expanded")

# --- KHỞI TẠO KẾT NỐI GOOGLE SHEETS ---
conn = st.connection("gsheets", type=GSheetsConnection)

FILE_SESSION = 'session_token.txt'
FILE_COLOR = 'theme_color.txt'
FILE_BG = 'background_custom.png'

FOLDER_AVATAR = 'avatars'
if not os.path.exists(FOLDER_AVATAR): os.makedirs(FOLDER_AVATAR)

BASE_COLS_KHO = ['Barcode', 'Tên Biệt Dược', 'Chương Trình', 'Nhóm Thuốc', 'Thành Phần', 'Đơn Vị Tính', 'Hạn Sử Dụng', 'Nhập Mới', 'Đã Xuất']
BASE_COLS_NS = ['Username', 'Password', 'Quyền', 'Họ Tên', 'SĐT', 'Gmail', 'MSSV', 'Lớp']
BASE_COLS_VT = ['Mã VT', 'Tên Vật Tư', 'Phân Loại', 'Đơn Vị Tính', 'Nhập Mới', 'Đã Xuất', 'Tình Trạng']

if not os.path.exists(FILE_COLOR):
    with open(FILE_COLOR, "w") as f: f.write("#004a99")
with open(FILE_COLOR, "r") as f: main_color = f.read().strip()

def load_data():
    try:
        df_k = conn.read(worksheet="KhoThuoc", ttl=0).dropna(how='all')
        df_ls = conn.read(worksheet="LichSu", ttl=0).dropna(how='all')
        df_ns = conn.read(worksheet="NhanSu", ttl=0).dropna(how='all')
        df_ct = conn.read(worksheet="ChuongTrinh", ttl=0).dropna(how='all')
        df_dt = conn.read(worksheet="DuTru", ttl=0).dropna(how='all')
        df_nhom = conn.read(worksheet="NhomThuoc", ttl=0).dropna(how='all')
        
        try: df_audit = conn.read(worksheet="NhatKy", ttl=0).dropna(how='all')
        except: df_audit = pd.DataFrame(columns=['Thời Gian', 'Người Dùng', 'Hành Động', 'Chi Tiết'])
        
        try: df_cd = conn.read(worksheet="ChoDuyet", ttl=0).dropna(how='all')
        except: df_cd = pd.DataFrame(columns=['Mã Phiếu', 'Thời Gian', 'Chương Trình', 'Nơi Xuất', 'Người Nhận', 'Người Yêu Cầu', 'Mã Thuốc', 'Tên Thuốc', 'Số Lượng', 'Trạng Thái'])

        try: df_vt = conn.read(worksheet="VatTu", ttl=0).dropna(how='all')
        except: df_vt = pd.DataFrame(columns=BASE_COLS_VT)

        for df in [df_k, df_ls, df_ns, df_ct, df_dt, df_nhom, df_audit, df_cd, df_vt]:
            if not df.empty:
                df.columns = [str(c).strip() for c in df.columns]
                
        if not df_k.empty and 'Hạn Sử Dụng' in df_k.columns:
            df_k['Hạn Sử Dụng'] = pd.to_datetime(df_k['Hạn Sử Dụng'], errors='coerce', dayfirst=True).dt.strftime('%d/%m/%Y').fillna(df_k['Hạn Sử Dụng'])
        
        if not df_ns.empty:
            rename_map = {'Tên người dùng': 'Username', 'Tên đăng nhập': 'Username', 'tài khoản': 'Username', 'Mật khẩu': 'Password'}
            df_ns.rename(columns=rename_map, inplace=True)
            if 'Username' not in df_ns.columns: df_ns.rename(columns={df_ns.columns[0]: 'Username'}, inplace=True)
            if 'Password' not in df_ns.columns and len(df_ns.columns) > 1: df_ns.rename(columns={df_ns.columns[1]: 'Password'}, inplace=True)
                
        if df_ns.empty:
            df_ns = pd.DataFrame([{'Username': 'DoanHoiSVKhoaY', 'Password': 'khoaY@298300A', 'Quyền': 'admin', 'Họ Tên': 'Admin Khoa Y', 'MSSV': 'Admin', 'Lớp': 'BCH', 'SĐT': '', 'Gmail': ''}])
                
        return df_k, df_ls, df_ns, df_ct, df_dt, df_nhom, df_audit, df_cd, df_vt
    except Exception as e:
        df_ns_default = pd.DataFrame([{'Username': 'DoanHoiSVKhoaY', 'Password': 'khoaY@298300A', 'Quyền': 'admin', 'Họ Tên': 'Admin Khoa Y', 'MSSV': 'Admin', 'Lớp': 'BCH', 'SĐT': '', 'Gmail': ''}])
        return pd.DataFrame(columns=BASE_COLS_KHO), pd.DataFrame(), df_ns_default, pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame(columns=['Thời Gian', 'Người Dùng', 'Hành Động', 'Chi Tiết']), pd.DataFrame(columns=['Mã Phiếu', 'Thời Gian', 'Chương Trình', 'Nơi Xuất', 'Người Nhận', 'Người Yêu Cầu', 'Mã Thuốc', 'Tên Thuốc', 'Số Lượng', 'Trạng Thái']), pd.DataFrame(columns=BASE_COLS_VT)

# ==========================================
# 2. HÀM HỖ TRỢ (UI, IN ẤN, LOGIC)
# ==========================================
def apply_styles(color, bg_path=None):
    bg_css = ""
    if bg_path and os.path.exists(bg_path):
        try:
            with open(bg_path, 'rb') as f: bin_str = base64.b64encode(f.read()).decode()
            bg_css = f'background-image: url("data:image/png;base64,{bin_str}"); background-size: cover; background-attachment: fixed;'
        except: pass
    st.markdown(f'''
    <style>
    .stApp {{ {bg_css} }}
    .main .block-container {{ background-color: rgba(255, 255, 255, 0.98); border-radius: 15px; padding: 30px; box-shadow: 0 4px 20px rgba(0,0,0,0.2); }}
    .stButton>button {{ background-color: {color}; color: white; border-radius: 8px; font-weight: bold; width: 100%; height: 45px; border: none; transition: 0.3s; }}
    div[data-testid="stMetricValue"] {{ color: {color}; font-weight: bold; font-size: 32px; }}
    .stTabs [aria-selected="true"] {{ background-color: {color} !important; color: white !important; border-radius: 5px; }}
    </style>
    ''', unsafe_allow_html=True)

def check_hsd_status(hsd_str):
    try:
        if pd.isna(hsd_str) or str(hsd_str).strip().lower() in ["", "nan", "nat", "none"]: return "❓ Trống"
        hsd_date = pd.to_datetime(str(hsd_str).strip(), dayfirst=True)
        today = pd.Timestamp.now().normalize()
        if hsd_date < today: return "❌ Hết hạn"
        elif hsd_date <= today + pd.Timedelta(days=180): return "⚠️ Sắp hết hạn"
        return "✅ Còn hạn"
    except: return "❓ Lỗi định dạng"

def color_hsd(val):
    colors = {"❌ Hết hạn": "#ff4b4b", "⚠️ Sắp hết hạn": "#ffa500", "✅ Còn hạn": "#28a745", "❓ Trống": "#6c757d", "❓ Lỗi định dạng": "#6c757d"}
    return f'color: {colors.get(val, "#6c757d")}; font-weight: bold'

def create_print_html(df, title):
    html = f"""
    <div style="font-family: Arial; padding: 25px; border: 2px solid {main_color}; border-radius: 10px; background: white; color: black;">
        <h2 style="text-align: center; color: {main_color}; text-transform: uppercase;">{title}</h2>
        <p style="text-align: center; font-style: italic;">Khoa Y - Trường Đại học Nguyễn Tất Thành</p>
        <hr style="border: 1px solid {main_color};">
        <p style="text-align: right; font-size: 12px;">Ngày xuất: {datetime.now().strftime('%d/%m/%Y %H:%M')}</p>
        <table style="width: 100%; border-collapse: collapse; margin-top: 15px;">
            <tr style="background-color: #f2f2f2;">{''.join([f'<th style="border: 1px solid #ddd; padding: 10px; text-align: left;">{c}</th>' for c in df.columns])}</tr>
            {''.join(['<tr>' + ''.join([f'<td style="border: 1px solid #ddd; padding: 8px;">{v}</td>' for v in r]) + '</tr>' for r in df.values])}
        </table>
    </div>
    <button onclick="window.print()" style="margin-top:15px; padding:12px 25px; background:{main_color}; color:white; border:none; border-radius:5px; cursor:pointer; font-weight:bold;">🖨️ XÁC NHẬN IN / XUẤT PDF</button>
    """
    return html

def create_qr_pdf_html(df_nhom_thuoc, ten_nhom):
    qr_cards = ""
    for _, row in df_nhom_thuoc.iterrows():
        val, ten = row['Barcode'], row['Tên Biệt Dược']
        qr = qrcode.make(val)
        b = BytesIO(); qr.save(b, format="PNG")
        qr_base64 = base64.b64encode(b.getvalue()).decode()
        qr_cards += f"""
        <div style="width: 30%; border: 1px solid #ccc; padding: 10px; margin: 5px; display: inline-block; text-align: center; border-radius: 5px;">
            <img src="data:image/png;base64,{qr_base64}" style="width: 100px; height: 100px;"><br>
            <b style="font-size: 14px;">{ten}</b><br><span style="font-size: 12px;">Mã: {val}</span>
        </div>"""
    return f"""<div style="font-family: Arial; padding: 20px; background: white; color: black;">
    <h3 style="text-align: center; color: {main_color};">DANH SÁCH MÃ QR - {ten_nhom.upper()}</h3>
    <div style="display: flex; flex-wrap: wrap; justify-content: center;">{qr_cards}</div>
    </div><button onclick="window.print()" style="margin-top:15px; padding:12px 25px; background:{main_color}; color:white; border:none; border-radius:5px; cursor:pointer; font-weight:bold;">🖨️ IN NHÃN QR</button>"""

def get_excel_template():
    df_temp = pd.DataFrame(columns=BASE_COLS_KHO)
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df_temp.to_excel(writer, index=False, sheet_name='Template')
    return output.getvalue()

def log_action(action, details):
    user = st.session_state.u_data.get('Username', 'Unknown')
    new_log = pd.DataFrame([{'Thời Gian': datetime.now().strftime("%d/%m/%Y %H:%M:%S"), 'Người Dùng': user, 'Hành Động': action, 'Chi Tiết': details}])
    st.session_state.df_audit = pd.concat([st.session_state.df_audit, new_log], ignore_index=True)

# ==========================================
# 3. QUẢN LÝ DỮ LIỆU
# ==========================================

def save_all():
    if not st.session_state.df_kho.empty:
        if 'Hạn Sử Dụng' in st.session_state.df_kho.columns:
            st.session_state.df_kho['Hạn Sử Dụng'] = pd.to_datetime(st.session_state.df_kho['Hạn Sử Dụng'], errors='coerce', dayfirst=True).dt.strftime('%d/%m/%Y').fillna(st.session_state.df_kho['Hạn Sử Dụng'])
        st.session_state.df_kho = st.session_state.df_kho.sort_values(by='Thành Phần', ascending=True)
    try:
        conn.update(worksheet="KhoThuoc", data=st.session_state.df_kho)
        conn.update(worksheet="LichSu", data=st.session_state.df_ls)
        conn.update(worksheet="NhanSu", data=st.session_state.df_ns)
        conn.update(worksheet="ChuongTrinh", data=st.session_state.df_ct)
        conn.update(worksheet="DuTru", data=st.session_state.df_dt)
        conn.update(worksheet="NhomThuoc", data=st.session_state.df_nhom)
        conn.update(worksheet="NhatKy", data=st.session_state.df_audit)
        conn.update(worksheet="ChoDuyet", data=st.session_state.df_cd)
        conn.update(worksheet="VatTu", data=st.session_state.df_vt) 
        st.toast("☁️ Đã đồng bộ lên Cloud!", icon='✅')
    except Exception as e:
        st.error(f"Lỗi kết nối Cloud: {e}")

def generate_code(nhom, df):
    words = str(nhom).split()
    prefix = (words[0][0] + (words[1][0] if len(words)>1 else words[0][1])).upper() if words else "TH"
    existing_codes = df['Barcode'].astype(str).tolist()
    nums = []
    for c in existing_codes:
        if c.startswith(prefix):
            base_num = c.split('-')[0][len(prefix):]
            if base_num.isdigit():
                nums.append(int(base_num))
    return f"{prefix}{max(nums)+1 if nums else 1:05d}"

if 'df_kho' not in st.session_state or 'df_cd' not in st.session_state or 'df_vt' not in st.session_state:
    st.session_state.df_kho, st.session_state.df_ls, st.session_state.df_ns, \
    st.session_state.df_ct, st.session_state.df_dt, st.session_state.df_nhom, \
    st.session_state.df_audit, st.session_state.df_cd, st.session_state.df_vt = load_data()

# --- LOGIN LOGIC ---
if "logged_in" not in st.session_state: st.session_state.logged_in = False

apply_styles(main_color, FILE_BG)

if not st.session_state.logged_in:
    st.markdown(f"<h1 style='text-align:center; color:{main_color};'>🏥 HỆ THỐNG QUẢN LÝ ĐOÀN - HỘI SINH VIÊN KHOA Y NTTU</h1>", unsafe_allow_html=True)
    _, c2, _ = st.columns([1, 1.2, 1])
    with c2:
        with st.form("login"):
            u = st.text_input("Tên đăng nhập")
            p = st.text_input("Mật khẩu", type="password")
            submit_button = st.form_submit_button("ĐĂNG NHẬP")
            
            if submit_button:
                ns = st.session_state.df_ns
                u_input = str(u).strip()
                p_input = str(p).strip()
                
                if not ns.empty and 'Username' in ns.columns:
                    user_match = ns[ns['Username'].astype(str).str.strip() == u_input]
                    
                    if not user_match.empty:
                        correct_p = str(user_match.iloc[0].get('Password', '')).strip()
                        if correct_p == p_input:
                            st.session_state.logged_in = True
                            st.session_state.u_data = user_match.iloc[0].to_dict()
                            log_action("Đăng nhập", "Đăng nhập hệ thống")
                            st.rerun()
                        else:
                            st.error("Mật khẩu không chính xác!")
                    else:
                        st.error("Tài khoản không tồn tại trên hệ thống!")
                else:
                    st.error("Lỗi cấu trúc file Sheets: Không tìm thấy cột Username!")
else:
    # ==========================================
    # CẤU TRÚC LẠI GIAO DIỆN: 4 MODULE CHÍNH
    # ==========================================
    with st.sidebar:
        ava_path = os.path.join(FOLDER_AVATAR, f"{st.session_state.u_data['Username']}.png")
        if os.path.exists(ava_path): st.image(ava_path, width=120)
        else: st.image("https://cdn-icons-png.flaticon.com/512/3135/3135715.png", width=120)
        
        st.write(f"Chào, **{st.session_state.u_data.get('Họ Tên', 'Admin')}**")
        if st.button("🚪 Đăng xuất", use_container_width=True):
            log_action("Đăng xuất", "Rời khỏi hệ thống")
            st.session_state.logged_in = False
            st.rerun()

        st.divider()
        st.markdown("### ⚙️ PHÂN HỆ QUẢN LÝ")
        # ĐÂY LÀ CHÌA KHÓA CHIA 4 MODULE:
        main_module = st.radio("Chọn Module hiển thị:", 
                               ["💊 Quản lý Kho Thuốc", 
                                "🛠️ Quản lý Vật Tư", 
                                "📅 Quản lý Hoạt Động",
                                "👥 Quản lý Nhân Sự"])
        st.divider()

        # --- CẬP NHẬT PHẦN THÔNG BÁO HỆ THỐNG CHI TIẾT ---
        if not st.session_state.df_kho.empty and main_module == "💊 Quản lý Kho Thuốc":
            df_cb = st.session_state.df_kho.copy()
            df_cb['Trạng Thái HSD'] = df_cb['Hạn Sử Dụng'].apply(check_hsd_status)
            df_cb['Tồn Kho'] = pd.to_numeric(df_cb['Nhập Mới'], errors='coerce').fillna(0) - pd.to_numeric(df_cb['Đã Xuất'], errors='coerce').fillna(0)
            
            # Lọc dữ liệu theo từng loại cảnh báo
            df_het_han = df_cb[df_cb['Trạng Thái HSD'] == '❌ Hết hạn']
            df_sap_het = df_cb[df_cb['Trạng Thái HSD'] == '⚠️ Sắp hết hạn']
            df_het_hang = df_cb[df_cb['Tồn Kho'] <= 0]
            df_ton_thap = df_cb[(df_cb['Tồn Kho'] > 0) & (df_cb['Tồn Kho'] <= 20)]
            
            if len(df_het_han) > 0 or len(df_sap_het) > 0 or len(df_ton_thap) > 0 or len(df_het_hang) > 0:
                st.markdown("🔔 **CẢNH BÁO KHO THUỐC**")
                
                if len(df_het_han) > 0: 
                    names = ", ".join(df_het_han['Tên Biệt Dược'].unique())
                    st.error(f"❌ **{len(df_het_han)} loại HẾT HẠN:** {names}")
                    
                if len(df_sap_het) > 0: 
                    names = ", ".join(df_sap_het['Tên Biệt Dược'].unique())
                    st.warning(f"⚠️ **{len(df_sap_het)} loại SẮP HẾT HẠN:** {names}")
                    
                if len(df_het_hang) > 0:
                    names = ", ".join(df_het_hang['Tên Biệt Dược'].unique())
                    st.error(f"❌ **{len(df_het_hang)} loại HẾT HÀNG:** {names}")
                    
                if len(df_ton_thap) > 0:
                    names = ", ".join(df_ton_thap['Tên Biệt Dược'].unique())
                    st.warning(f"🔽 **{len(df_ton_thap)} loại SẮP CẠN KHO:** {names}")

        st.write("🎨 **Tùy chỉnh Giao diện**")
        nc = st.color_picker("Màu chủ đạo", main_color)
        if nc != main_color:
            with open(FILE_COLOR, "w") as f: f.write(nc)
            st.rerun()
        bg_up = st.file_uploader("🖼️ Thay hình nền", type=['png', 'jpg'])
        if bg_up:
            with open(FILE_BG, "wb") as f: f.write(bg_up.getbuffer())
            st.rerun()

    # ==========================================
    # MODULE 1: QUẢN LÝ KHO THUỐC
    # ==========================================
    if main_module == "💊 Quản lý Kho Thuốc":
        st.markdown(f"<h2 style='color:{main_color};'>💊 PHÂN HỆ QUẢN LÝ KHO THUỐC</h2>", unsafe_allow_html=True)
        # Đã bứng tab Dự trù & Chương trình đi nơi khác
        tabs_thuoc = st.tabs(["📊 DASHBOARD", "📤 XUẤT THUỐC", "📥 NHẬP KHO", "🏷️ NHÓM", "📦 KHO TỔNG"])

        with tabs_thuoc[0]: 
            st.session_state.df_kho['Tồn Kho'] = pd.to_numeric(st.session_state.df_kho['Nhập Mới'], errors='coerce').fillna(0) - pd.to_numeric(st.session_state.df_kho['Đã Xuất'], errors='coerce').fillna(0)
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Mặt hàng Thuốc", len(st.session_state.df_kho))
            c2.metric("Tổng tồn Thuốc", int(st.session_state.df_kho['Tồn Kho'].sum()))
            c3.metric("Chương trình", len(st.session_state.df_ct))
            c4.metric("Phiếu chờ duyệt", len(st.session_state.df_cd[st.session_state.df_cd['Trạng Thái'] == 'Chờ duyệt']))

            st.divider()
            st.markdown("#### 📈 Thống kê & Biểu đồ trực quan")
            c_chart1, c_chart2 = st.columns(2)
            
            with c_chart1:
                st.markdown("**Top 5 Nhóm thuốc có số lượng tồn nhiều nhất**")
                if not st.session_state.df_kho.empty:
                    df_chart_nhom = st.session_state.df_kho.groupby('Nhóm Thuốc')['Tồn Kho'].sum().nlargest(5).reset_index()
                    st.bar_chart(data=df_chart_nhom, x='Nhóm Thuốc', y='Tồn Kho', use_container_width=True)
            
            with c_chart2:
                st.markdown("**Top 5 Thuốc được xuất dùng nhiều nhất**")
                if not st.session_state.df_ls.empty and 'Số Lượng' in st.session_state.df_ls.columns and 'Tên Thuốc' in st.session_state.df_ls.columns:
                    st.session_state.df_ls['Số Lượng'] = pd.to_numeric(st.session_state.df_ls['Số Lượng'], errors='coerce').fillna(0)
                    df_xuat_thuc = st.session_state.df_ls[st.session_state.df_ls['Số Lượng'] > 0]
                    if not df_xuat_thuc.empty:
                        df_chart_xuat = df_xuat_thuc.groupby('Tên Thuốc')['Số Lượng'].sum().nlargest(5).reset_index()
                        st.bar_chart(data=df_chart_xuat, x='Tên Thuốc', y='Số Lượng', use_container_width=True)

        with tabs_thuoc[1]: 
            st.subheader("📤 Xuất thuốc chiến dịch")
            ct_list = st.session_state.df_ct['Tên Chương Trình'].tolist() if not st.session_state.df_ct.empty else ["Kho Tổng"]
            sel_ct = st.selectbox("Chọn chương trình:", ct_list)
            
            mode = st.radio("Tìm kiếm:", ["Quét mã QR/Barcode", "Chọn danh mục"], horizontal=True)
            res_x = pd.DataFrame()
            if mode == "Quét mã QR/Barcode":
                bc_x = st.text_input("📳 Quét mã thuốc...")
                if bc_x: res_x = st.session_state.df_kho[(st.session_state.df_kho['Barcode'] == str(bc_x)) & (st.session_state.df_kho['Chương Trình'] == sel_ct)]
            else:
                df_l = st.session_state.df_kho[st.session_state.df_kho['Chương Trình'] == sel_ct]
                t_t = st.selectbox("🔍 Tên biệt dược", ["---"] + sorted(df_l['Tên Biệt Dược'].unique().tolist()))
                if t_t != "---": res_x = df_l[df_l['Tên Biệt Dược'] == t_t]

            if not res_x.empty:
                st.success(f"Khớp thuốc: {res_x.iloc[0]['Tên Biệt Dược']} | Lô HSD: {res_x.iloc[0]['Hạn Sử Dụng']}")
                cx1, cx2, cx3 = st.columns(3)
                lx, px, sx = cx1.text_input("Nơi xuất"), cx2.text_input("Người nhận"), cx3.number_input("Số lượng", min_value=1)
                
                quyen_user = st.session_state.u_data.get('Quyền', 'user')
                btn_label = "🚀 XÁC NHẬN CẤP THUỐC (ADMIN)" if quyen_user == 'admin' else "📨 GỬI YÊU CẦU XUẤT THUỐC"
                
                if st.button(btn_label):
                    idx = st.session_state.df_kho[st.session_state.df_kho['Barcode'] == res_x.iloc[0]['Barcode']].index[0]
                    if st.session_state.df_kho.at[idx, 'Tồn Kho'] >= sx:
                        if quyen_user == 'admin':
                            st.session_state.df_kho.at[idx, 'Đã Xuất'] += sx
                            new_h = pd.DataFrame([{'Thời Gian': datetime.now().strftime("%d/%m/%Y %H:%M"), 'Chương Trình': sel_ct, 'Nơi Xuất': lx, 'Người Xuất': px, 'Người Thực Hiện': st.session_state.u_data.get('Họ Tên', 'Admin'), 'Tên Thuốc': res_x.iloc[0]['Tên Biệt Dược'], 'Số Lượng': sx}])
                            st.session_state.df_ls = pd.concat([st.session_state.df_ls, new_h], ignore_index=True)
                            log_action("Xuất thuốc", f"Xuất trực tiếp {sx} {res_x.iloc[0]['Tên Biệt Dược']}")
                            save_all()
                            st.markdown(create_print_html(new_h, "PHIẾU XUẤT THUỐC"), unsafe_allow_html=True)
                        else:
                            ma_phieu = f"PX-{datetime.now().strftime('%Y%m%d%H%M%S')}"
                            new_req = pd.DataFrame([{'Mã Phiếu': ma_phieu, 'Thời Gian': datetime.now().strftime("%d/%m/%Y %H:%M"), 'Chương Trình': sel_ct, 'Nơi Xuất': lx, 'Người Nhận': px, 'Người Yêu Cầu': st.session_state.u_data.get('Họ Tên', 'User'), 'Mã Thuốc': res_x.iloc[0]['Barcode'], 'Tên Thuốc': res_x.iloc[0]['Tên Biệt Dược'], 'Số Lượng': sx, 'Trạng Thái': 'Chờ duyệt'}])
                            st.session_state.df_cd = pd.concat([st.session_state.df_cd, new_req], ignore_index=True)
                            log_action("Yêu cầu xuất", f"Gửi phiếu {ma_phieu} (SL: {sx})")
                            save_all()
                            st.success(f"✅ Đã gửi yêu cầu ({ma_phieu}) thành công! Vui lòng chờ Admin duyệt.")
                    else: st.error("Không đủ số lượng trong kho!")
                    
            if st.session_state.u_data.get('Quyền') == 'admin':
                st.divider()
                st.markdown("### 📋 DANH SÁCH YÊU CẦU CHỜ DUYỆT")
                pending_df = st.session_state.df_cd[st.session_state.df_cd['Trạng Thái'] == 'Chờ duyệt']
                if not pending_df.empty:
                    for req_idx, req_row in pending_df.iterrows():
                        with st.expander(f"📦 Phiếu {req_row['Mã Phiếu']} | 💊 {req_row['Tên Thuốc']} (SL: {req_row['Số Lượng']})", expanded=True):
                            st.write(f"- **Chương trình:** {req_row['Chương Trình']} | **Nơi xuất:** {req_row['Nơi Xuất']}")
                            st.write(f"- **Người nhận:** {req_row['Người Nhận']} | **Người yêu cầu:** {req_row['Người Yêu Cầu']} | **TG:** {req_row['Thời Gian']}")
                            
                            col_d1, col_d2 = st.columns(2)
                            if col_d1.button(f"✅ Duyệt Phiếu {req_row['Mã Phiếu']}"):
                                idx_kho = st.session_state.df_kho[st.session_state.df_kho['Barcode'] == req_row['Mã Thuốc']].index
                                if not idx_kho.empty and st.session_state.df_kho.at[idx_kho[0], 'Tồn Kho'] >= req_row['Số Lượng']:
                                    st.session_state.df_kho.at[idx_kho[0], 'Đã Xuất'] += req_row['Số Lượng']
                                    new_ls = pd.DataFrame([{'Thời Gian': datetime.now().strftime("%d/%m/%Y %H:%M"), 'Chương Trình': req_row['Chương Trình'], 'Nơi Xuất': req_row['Nơi Xuất'], 'Người Xuất': req_row['Người Nhận'], 'Người Thực Hiện': f"{req_row['Người Yêu Cầu']} (Admin duyệt)", 'Tên Thuốc': req_row['Tên Thuốc'], 'Số Lượng': req_row['Số Lượng']}])
                                    st.session_state.df_ls = pd.concat([st.session_state.df_ls, new_ls], ignore_index=True)
                                    st.session_state.df_cd.at[req_idx, 'Trạng Thái'] = 'Đã duyệt'
                                    log_action("Duyệt phiếu", f"Duyệt xuất {req_row['Số Lượng']} {req_row['Tên Thuốc']}")
                                    save_all()
                                    st.success(f"Đã duyệt thành công phiếu {req_row['Mã Phiếu']}!")
                                    st.rerun()
                                else:
                                    st.error("Lỗi: Số lượng trong kho không đủ để duyệt phiếu này!")
                                    
                            if col_d2.button(f"❌ Từ chối Phiếu {req_row['Mã Phiếu']}"):
                                st.session_state.df_cd.at[req_idx, 'Trạng Thái'] = 'Từ chối'
                                log_action("Từ chối phiếu", f"Hủy phiếu {req_row['Mã Phiếu']}")
                                save_all()
                                st.warning(f"Đã từ chối phiếu {req_row['Mã Phiếu']}")
                                st.rerun()
                else:
                    st.info("Hiện không có yêu cầu xuất thuốc nào đang chờ duyệt.")

            st.divider()
            with st.expander("🔙 NHẬP TRẢ THUỐC (Hoàn kho sau chiến dịch)", expanded=False):
                st.info("Sử dụng tính năng này khi kết thúc đợt khám và còn dư thuốc cần trả lại vào kho.")
                ret_ct = st.selectbox("Chọn chương trình hoàn trả:", ct_list, key="ret_ct")
                if not st.session_state.df_ls.empty and 'Chương Trình' in st.session_state.df_ls.columns:
                    df_exported = st.session_state.df_ls[st.session_state.df_ls['Chương Trình'] == ret_ct]
                else: df_exported = pd.DataFrame()
                    
                if not df_exported.empty:
                    ret_thuoc = st.selectbox("Chọn thuốc cần trả:", sorted(df_exported['Tên Thuốc'].unique().tolist()), key="ret_thuoc")
                    df_kho_match = st.session_state.df_kho[st.session_state.df_kho['Tên Biệt Dược'] == ret_thuoc]
                    if not df_kho_match.empty:
                        ret_lo = st.selectbox("Chọn Lô/Mã cần trả vào:", df_kho_match['Barcode'].tolist(), format_func=lambda x: f"Mã: {x} (HSD: {df_kho_match[df_kho_match['Barcode']==x]['Hạn Sử Dụng'].values[0]})", key="ret_lo")
                        ret_sl = st.number_input("Số lượng trả lại kho", min_value=1, key="ret_sl")
                        if st.button("🔄 XÁC NHẬN TRẢ KHO"):
                            idx_ret = st.session_state.df_kho[st.session_state.df_kho['Barcode'] == ret_lo].index[0]
                            cur_xuat = st.session_state.df_kho.at[idx_ret, 'Đã Xuất']
                            if cur_xuat >= ret_sl: st.session_state.df_kho.at[idx_ret, 'Đã Xuất'] -= ret_sl
                            else:
                                st.session_state.df_kho.at[idx_ret, 'Đã Xuất'] = 0
                                st.session_state.df_kho.at[idx_ret, 'Nhập Mới'] += (ret_sl - cur_xuat)
                            
                            new_h_ret = pd.DataFrame([{'Thời Gian': datetime.now().strftime("%d/%m/%Y %H:%M"), 'Chương Trình': ret_ct, 'Nơi Xuất': "Kho Tổng (Hoàn Trả)", 'Người Xuất': "Hệ thống", 'Người Thực Hiện': st.session_state.u_data.get('Họ Tên', 'Admin'), 'Tên Thuốc': ret_thuoc, 'Số Lượng': -ret_sl}])
                            st.session_state.df_ls = pd.concat([st.session_state.df_ls, new_h_ret], ignore_index=True)
                            log_action("Nhập trả thuốc", f"Trả {ret_sl} {ret_thuoc} từ {ret_ct}")
                            save_all(); st.success("✅ Đã hoàn trả thuốc vào kho thành công!"); st.rerun()
                    else: st.warning("Thuốc này không còn tồn tại trong danh mục kho tổng.")
                else: st.warning("Chưa có dữ liệu xuất thuốc cho chương trình này.")

        with tabs_thuoc[2]: 
            st.subheader("📥 Nhập kho & Import Excel")
            ct_list_in = st.session_state.df_ct['Tên Chương Trình'].tolist() if not st.session_state.df_ct.empty else ["Kho Tổng"]
            ct_in = st.selectbox("Nhập cho đợt", ct_list_in)
            c_n1, c_n2 = st.columns(2)
            with c_n1:
                with st.form("nhap_tay"):
                    st.write("#### 📝 Nhập thủ công")
                    nt = st.text_input("Tên biệt dược")
                    tp = st.text_input("Thành phần")
                    nhom_list = st.session_state.df_nhom['Tên Nhóm'].tolist() if not st.session_state.df_nhom.empty else ["Khác"]
                    nnh = st.selectbox("Nhóm thuốc", nhom_list)
                    dv = st.selectbox("Đơn vị", ["Viên", "Gói", "Chai", "Tuýp", "Ống"])
                    sl = st.number_input("Số lượng", min_value=1)
                    hsd = st.date_input("Hạn dùng", format="DD/MM/YYYY")
                    
                    if st.form_submit_button("➕ THÊM VÀO KHO"):
                        hsd_str = hsd.strftime('%d/%m/%Y')
                        mask_exact = (st.session_state.df_kho['Tên Biệt Dược'] == nt) & (st.session_state.df_kho['Hạn Sử Dụng'] == hsd_str)
                        mask_name = (st.session_state.df_kho['Tên Biệt Dược'] == nt)
                        
                        if mask_exact.any(): st.session_state.df_kho.loc[mask_exact, 'Nhập Mới'] = pd.to_numeric(st.session_state.df_kho.loc[mask_exact, 'Nhập Mới']) + sl
                        elif mask_name.any():
                            base_code = str(st.session_state.df_kho.loc[mask_name, 'Barcode'].values[0]).split('-')[0]
                            count_batches = len(st.session_state.df_kho[st.session_state.df_kho['Barcode'].str.startswith(base_code, na=False)])
                            new_r = pd.DataFrame([{'Barcode': f"{base_code}-{count_batches + 1}", 'Tên Biệt Dược': nt, 'Chương Trình': ct_in, 'Nhóm Thuốc': nnh, 'Thành Phần': tp, 'Đơn Vị Tính': dv, 'Hạn Sử Dụng': hsd_str, 'Nhập Mới': sl, 'Đã Xuất': 0}])
                            st.session_state.df_kho = pd.concat([st.session_state.df_kho, new_r], ignore_index=True)
                        else:
                            new_r = pd.DataFrame([{'Barcode': generate_code(nnh, st.session_state.df_kho), 'Tên Biệt Dược': nt, 'Chương Trình': ct_in, 'Nhóm Thuốc': nnh, 'Thành Phần': tp, 'Đơn Vị Tính': dv, 'Hạn Sử Dụng': hsd_str, 'Nhập Mới': sl, 'Đã Xuất': 0}])
                            st.session_state.df_kho = pd.concat([st.session_state.df_kho, new_r], ignore_index=True)
                        
                        log_action("Nhập tay", f"Nhập {sl} {nt}")    
                        save_all(); st.rerun()
            with c_n2:
                st.write("#### 📊 Import Excel hàng loạt")
                st.download_button(label="📥 Tải biểu mẫu Excel mẫu", data=get_excel_template(), file_name="Bieu_Mau_Nhap_Thuoc.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
                f_ex = st.file_uploader("Chọn file Excel thuốc (.xlsx)", type=['xlsx'])
                
                if f_ex and st.button("🚀 NẠP DỮ LIỆU EXCEL"):
                    df_new = pd.read_excel(f_ex)
                    for col in BASE_COLS_KHO:
                        if col not in df_new.columns: df_new[col] = 0 if col in ['Nhập Mới', 'Đã Xuất'] else ""
                    
                    for idx, row in df_new.iterrows():
                        ten_thuoc = str(row.get('Tên Biệt Dược', '')).strip()
                        if not ten_thuoc or ten_thuoc == 'nan': continue
                        raw_hsd = row.get('Hạn Sử Dụng', '')
                        try:
                            if isinstance(raw_hsd, datetime): hsd_str = raw_hsd.strftime('%d/%m/%Y')
                            else: 
                                hsd_str = pd.to_datetime(str(raw_hsd).strip(), errors='coerce', dayfirst=True).strftime('%d/%m/%Y')
                                if pd.isna(hsd_str): hsd_str = str(raw_hsd).strip().split()[0]
                        except: hsd_str = str(raw_hsd)
                            
                        nhom = str(row.get('Nhóm Thuốc', 'Khác')).strip()
                        sl_nhap = pd.to_numeric(row.get('Nhập Mới', 0), errors='coerce')
                        if pd.isna(sl_nhap): sl_nhap = 0

                        mask_exact = (st.session_state.df_kho['Tên Biệt Dược'] == ten_thuoc) & (st.session_state.df_kho['Hạn Sử Dụng'] == hsd_str)
                        mask_name = (st.session_state.df_kho['Tên Biệt Dược'] == ten_thuoc)
                        
                        if mask_exact.any(): st.session_state.df_kho.loc[mask_exact, 'Nhập Mới'] = pd.to_numeric(st.session_state.df_kho.loc[mask_exact, 'Nhập Mới']) + sl_nhap
                        elif mask_name.any():
                            base_code = str(st.session_state.df_kho.loc[mask_name, 'Barcode'].values[0]).split('-')[0]
                            count_batches = len(st.session_state.df_kho[st.session_state.df_kho['Barcode'].str.startswith(base_code, na=False)])
                            new_row = row.copy()
                            new_row['Barcode'] = f"{base_code}-{count_batches + 1}"
                            new_row['Hạn Sử Dụng'] = hsd_str
                            new_row['Chương Trình'] = ct_in
                            new_row['Đã Xuất'] = 0
                            st.session_state.df_kho = pd.concat([st.session_state.df_kho, pd.DataFrame([new_row])], ignore_index=True)
                        else:
                            new_row = row.copy()
                            new_row['Barcode'] = generate_code(nhom, st.session_state.df_kho)
                            new_row['Hạn Sử Dụng'] = hsd_str
                            new_row['Chương Trình'] = ct_in
                            new_row['Đã Xuất'] = 0
                            st.session_state.df_kho = pd.concat([st.session_state.df_kho, pd.DataFrame([new_row])], ignore_index=True)
                    log_action("Nhập Excel", f"Import file {f_ex.name}")
                    save_all(); st.rerun()

        with tabs_thuoc[3]: 
            st.subheader("🏷️ Quản lý Nhóm & Mã QR")
            col_c, col_g = st.columns([1, 1.5])
            with col_c:
                st.markdown("#### 🔄 Tạo mã quy định")
                nhom_list2 = st.session_state.df_nhom['Tên Nhóm'].tolist() if not st.session_state.df_nhom.empty else ["Khác"]
                nh_sel = st.selectbox("Chọn nhóm thuốc:", nhom_list2)
                new_c = generate_code(nh_sel, st.session_state.df_kho)
                st.info(f"Mã gợi ý tiếp theo: **{new_c}**")
                if st.button("🖨️ Xem mã QR"):
                    q_buf = BytesIO(); qrcode.make(new_c).save(q_buf, format="PNG")
                    st.image(q_buf, width=150)
            with col_g:
                st.markdown("#### ⚙️ Quản lý Danh mục Nhóm thuốc")
                if st.session_state.u_data.get('Quyền') == 'admin':
                    new_n = st.text_input("Tên nhóm mới (VD: Nội tiết)")
                    if st.button("➕ Thêm Nhóm"):
                        if new_n and (st.session_state.df_nhom.empty or new_n not in st.session_state.df_nhom['Tên Nhóm'].values):
                            st.session_state.df_nhom = pd.concat([st.session_state.df_nhom, pd.DataFrame({'Tên Nhóm': [new_n]})], ignore_index=True)
                            log_action("Thêm nhóm", f"Nhóm {new_n}")
                            save_all(); st.rerun()
                    ed_nh = st.data_editor(st.session_state.df_nhom, use_container_width=True, num_rows="dynamic", key="editor_nhom")
                    if st.button("💾 Lưu Nhóm"): st.session_state.df_nhom = ed_nh; log_action("Sửa nhóm", "Cập nhật danh mục nhóm"); save_all(); st.rerun()
                else: st.dataframe(st.session_state.df_nhom, use_container_width=True)

        with tabs_thuoc[4]: 
            st.subheader("📦 Kho tổng & HSD")
            st.markdown("#### 🛠️ Tùy chọn quản lý nâng cao")
            col_t1, col_t2, col_t3 = st.columns(3)
            with col_t1:
                if st.button("🔤 Sắp xếp A-Z (Theo Tên)"):
                    st.session_state.df_kho = st.session_state.df_kho.sort_values(by='Tên Biệt Dược').reset_index(drop=True)
                    save_all(); st.rerun()
            with col_t2:
                tim_kiem = st.text_input("🔍 Lọc theo tên thuốc:")
            with col_t3:
                if st.session_state.u_data.get('Quyền') == 'admin':
                    thuoc_xoa = st.selectbox("🗑️ Chọn thuốc để xóa:", ["---"] + sorted(st.session_state.df_kho['Tên Biệt Dược'].unique().tolist()))
                    if st.button("❌ Xác nhận xóa") and thuoc_xoa != "---":
                        st.session_state.df_kho = st.session_state.df_kho[st.session_state.df_kho['Tên Biệt Dược'] != thuoc_xoa]
                        log_action("Xóa thuốc", f"Đã xóa toàn bộ {thuoc_xoa}")
                        save_all(); st.rerun()
            st.divider()

            if st.session_state.u_data.get('Quyền') == 'admin':
                with st.expander("✏️ Cập nhật & Chỉnh sửa chi tiết thuốc", expanded=False):
                    if not st.session_state.df_kho.empty:
                        edit_sel = st.selectbox("🔍 Chọn thuốc cần sửa (Dựa theo Mã & Tên):", st.session_state.df_kho['Barcode'] + " - " + st.session_state.df_kho['Tên Biệt Dược'], key="sel_edit_thuoc")
                        
                        if edit_sel:
                            ma_edit = edit_sel.split(" - ")[0]
                            idx_edit = st.session_state.df_kho[st.session_state.df_kho['Barcode'] == ma_edit].index[0]
                            row_edit = st.session_state.df_kho.loc[idx_edit]
                            
                            with st.form("form_edit_thuoc"):
                                c_e1, c_e2 = st.columns(2)
                                new_ten = c_e1.text_input("Tên biệt dược", value=str(row_edit.get('Tên Biệt Dược', '')))
                                new_tp = c_e2.text_input("Thành phần", value=str(row_edit.get('Thành Phần', '')))
                                
                                c_e3, c_e4, c_e5 = st.columns(3)
                                nhom_list_e = st.session_state.df_nhom['Tên Nhóm'].tolist() if not st.session_state.df_nhom.empty else ["Khác"]
                                current_nhom = str(row_edit.get('Nhóm Thuốc', 'Khác'))
                                idx_nhom = nhom_list_e.index(current_nhom) if current_nhom in nhom_list_e else 0
                                new_nhom = c_e3.selectbox("Nhóm thuốc", nhom_list_e, index=idx_nhom)
                                
                                dv_list = ["Viên", "Gói", "Chai", "Tuýp", "Ống"]
                                current_dv = str(row_edit.get('Đơn Vị Tính', 'Viên'))
                                idx_dv = dv_list.index(current_dv) if current_dv in dv_list else 0
                                new_dv = c_e4.selectbox("Đơn vị tính", dv_list, index=idx_dv)
                                
                                new_hsd = c_e5.text_input("Hạn sử dụng (DD/MM/YYYY)", value=str(row_edit.get('Hạn Sử Dụng', '')))
                                
                                c_e6, c_e7 = st.columns(2)
                                try: val_nhap = int(float(row_edit.get('Nhập Mới', 0)))
                                except: val_nhap = 0
                                new_nhap = c_e6.number_input("Số lượng Nhập Mới", value=val_nhap, min_value=0)
                                
                                try: val_xuat = int(float(row_edit.get('Đã Xuất', 0)))
                                except: val_xuat = 0
                                new_xuat = c_e7.number_input("Số lượng Đã Xuất", value=val_xuat, min_value=0)
                                
                                if st.form_submit_button("💾 LƯU THAY ĐỔI"):
                                    st.session_state.df_kho.at[idx_edit, 'Tên Biệt Dược'] = new_ten
                                    st.session_state.df_kho.at[idx_edit, 'Thành Phần'] = new_tp
                                    st.session_state.df_kho.at[idx_edit, 'Nhóm Thuốc'] = new_nhom
                                    st.session_state.df_kho.at[idx_edit, 'Đơn Vị Tính'] = new_dv
                                    st.session_state.df_kho.at[idx_edit, 'Hạn Sử Dụng'] = new_hsd
                                    st.session_state.df_kho.at[idx_edit, 'Nhập Mới'] = new_nhap
                                    st.session_state.df_kho.at[idx_edit, 'Đã Xuất'] = new_xuat
                                    log_action("Sửa thuốc", f"Đã sửa thông tin mã {ma_edit}")
                                    save_all(); st.success("✅ Đã cập nhật thông tin thuốc thành công!"); st.rerun()
            st.divider()
            
            st.markdown("**📊 Thống kê nhanh kho thuốc**")
            if not st.session_state.df_kho.empty:
                df_stat = st.session_state.df_kho.groupby('Nhóm Thuốc').agg(Số_Mặt_Hàng=('Tên Biệt Dược', 'nunique'), Tổng_Tồn_Kho=('Tồn Kho', 'sum')).reset_index()
                st.dataframe(df_stat, use_container_width=True)
            st.divider()
            
            c_in1, c_in2 = st.columns(2)
            with c_in1:
                if st.button("🖨️ IN DANH MỤC KHO TỔNG"):
                    st.markdown(create_print_html(st.session_state.df_kho[['Tên Biệt Dược', 'Nhóm Thuốc', 'Đơn Vị Tính', 'Hạn Sử Dụng', 'Tồn Kho']], "DANH MỤC KHO TỔNG"), unsafe_allow_html=True)
            with c_in2:
                if not st.session_state.df_kho.empty:
                    nhom_in_qr = st.selectbox("Chọn nhóm để in QR hàng loạt:", ["Tất cả"] + st.session_state.df_kho['Nhóm Thuốc'].unique().tolist())
                    if st.button("🖨️ IN QR HÀNG LOẠT"):
                        df_in_qr = st.session_state.df_kho if nhom_in_qr == "Tất cả" else st.session_state.df_kho[st.session_state.df_kho['Nhóm Thuốc'] == nhom_in_qr]
                        st.markdown(create_qr_pdf_html(df_in_qr, f"NHÓM {nhom_in_qr}"), unsafe_allow_html=True)
            
            if not st.session_state.df_kho.empty:
                df_view = st.session_state.df_kho.copy()
                if tim_kiem: df_view = df_view[df_view['Tên Biệt Dược'].str.contains(tim_kiem, case=False, na=False)]
                df_view['Trạng Thái HSD'] = df_view['Hạn Sử Dụng'].apply(check_hsd_status)
                styled_df = df_view.style.map(color_hsd, subset=['Trạng Thái HSD'])
                
                if st.session_state.u_data.get('Quyền') == 'admin':
                    ed_k = st.data_editor(styled_df, use_container_width=True, hide_index=True, num_rows="dynamic", key="editor_kho")
                    if st.button("💾 Lưu thay đổi Kho"):
                        if tim_kiem: st.warning("⚠️ Vui lòng xóa nội dung trong ô 'Lọc theo tên thuốc' trước khi Lưu!")
                        else:
                            st.session_state.df_kho = ed_k[[c for c in ed_k.columns if c != 'Trạng Thái HSD']]
                            log_action("Sửa kho nhanh", "Sửa trực tiếp trên bảng")
                            save_all(); st.rerun()
                else:
                    st.dataframe(styled_df, use_container_width=True)

    # ==========================================
    # MODULE 2: QUẢN LÝ VẬT TƯ
    # ==========================================
    elif main_module == "🛠️ Quản lý Vật Tư":
        st.markdown(f"<h2 style='color:{main_color};'>🛠️ PHÂN HỆ QUẢN LÝ VẬT TƯ Y TẾ</h2>", unsafe_allow_html=True)
        
        tabs_vt = st.tabs(["📥 NHẬP VẬT TƯ", "📋 DANH MỤC VẬT TƯ", "📤 XUẤT THEO CHƯƠNG TRÌNH"])
        
        if not st.session_state.df_vt.empty:
            st.session_state.df_vt['Tồn Kho VT'] = pd.to_numeric(st.session_state.df_vt['Nhập Mới'], errors='coerce').fillna(0) - pd.to_numeric(st.session_state.df_vt['Đã Xuất'], errors='coerce').fillna(0)
        
        with tabs_vt[0]:
            st.subheader("📥 Nhập Vật Tư / Thiết Bị Mới")
            with st.form("nhap_vattu"):
                c_vt1, c_vt2 = st.columns(2)
                vt_ten = c_vt1.text_input("Tên Vật tư/Thiết bị")
                vt_loai = c_vt2.selectbox("Phân loại", ["Tiêu hao (Bông, găng tay...)", "Thiết bị (Máy HA, tai nghe...)"])
                
                c_vt3, c_vt4, c_vt5 = st.columns(3)
                vt_dv = c_vt3.text_input("Đơn vị (Hộp, Cái, Cuộn...)")
                vt_sl = c_vt4.number_input("Số lượng nhập", min_value=1)
                vt_tt = c_vt5.selectbox("Tình trạng ban đầu", ["Bình thường", "Cần kiểm tra"])
                
                if st.form_submit_button("Nhập vào kho Vật Tư"):
                    if vt_ten:
                        ma_vt_moi = f"VT{datetime.now().strftime('%y%m%d%H%M')}"
                        loai_ngan = "Tiêu hao" if "Tiêu hao" in vt_loai else "Thiết bị"
                        new_vt = pd.DataFrame([{'Mã VT': ma_vt_moi, 'Tên Vật Tư': vt_ten, 'Phân Loại': loai_ngan, 'Đơn Vị Tính': vt_dv, 'Nhập Mới': vt_sl, 'Đã Xuất': 0, 'Tình Trạng': vt_tt}])
                        st.session_state.df_vt = pd.concat([st.session_state.df_vt, new_vt], ignore_index=True)
                        log_action("Nhập vật tư", f"Nhập {vt_sl} {vt_ten}")
                        save_all()
                        st.success(f"Đã thêm vật tư {vt_ten} thành công!")
                        st.rerun()

        with tabs_vt[1]:
            st.subheader("📋 Danh mục Kho Vật Tư & Thiết bị")
            if not st.session_state.df_vt.empty:
                df_vt_view = st.session_state.df_vt[['Mã VT', 'Tên Vật Tư', 'Phân Loại', 'Đơn Vị Tính', 'Tồn Kho VT', 'Tình Trạng']]
                
                if st.session_state.u_data.get('Quyền') == 'admin':
                    ed_vt = st.data_editor(df_vt_view, use_container_width=True, hide_index=True, key="editor_vt")
                    if st.button("💾 Lưu thay đổi Vật Tư"):
                        st.session_state.df_vt['Tên Vật Tư'] = ed_vt['Tên Vật Tư']
                        st.session_state.df_vt['Phân Loại'] = ed_vt['Phân Loại']
                        st.session_state.df_vt['Đơn Vị Tính'] = ed_vt['Đơn Vị Tính']
                        st.session_state.df_vt['Tình Trạng'] = ed_vt['Tình Trạng']
                        log_action("Sửa bảng Vật tư", "Cập nhật trực tiếp trên bảng")
                        save_all()
                        st.rerun()
                else:
                    st.dataframe(df_vt_view, use_container_width=True, hide_index=True)
            else:
                st.info("Kho vật tư hiện đang trống. Hãy nhập vật tư mới ở tab bên cạnh!")

        with tabs_vt[2]:
            st.subheader("📤 Xuất / Mượn Vật tư cho Chương trình")
            if not st.session_state.df_vt.empty:
                loai_nhap_ct = st.radio("Cách nhập Tên Chương trình:", ["Chọn từ danh mục có sẵn", "Nhập thủ công (Tên mới)"], horizontal=True)
                
                if loai_nhap_ct == "Chọn từ danh mục có sẵn":
                    ct_list_vt = st.session_state.df_ct['Tên Chương Trình'].tolist() if not st.session_state.df_ct.empty else ["Kho Tổng"]
                    sel_ct_vt = st.selectbox("Chọn chương trình:", ct_list_vt, key="sel_ct_vt")
                else:
                    sel_ct_vt = st.text_input("Gõ tên Chương trình (VD: Hội thao truyền thống 2026):", key="txt_ct_vt")
                
                with st.expander("📤 Xuất tiêu hao / Cho mượn thiết bị", expanded=True):
                    with st.form("xuat_vattu"):
                        vt_sel = st.selectbox("Chọn Vật tư cần xuất:", st.session_state.df_vt['Tên Vật Tư'].tolist())
                        
                        c_x1, c_x2 = st.columns(2)
                        vt_sl_xuat = c_x1.number_input("Số lượng xuất/mượn", min_value=1)
                        vt_noi_xuat = c_x2.text_input("Nơi xuất / Danh mục xuất (Tùy chọn)")
                        
                        vt_nguoi = st.text_input("Người nhận/mượn (Tên SV/Ban)")
                        
                        if st.form_submit_button("Xác nhận xuất Vật tư"):
                            if not sel_ct_vt:
                                st.error("⚠️ Vui lòng nhập hoặc chọn Tên chương trình trước khi xuất!")
                            else:
                                idx_vt = st.session_state.df_vt[st.session_state.df_vt['Tên Vật Tư'] == vt_sel].index[0]
                                if st.session_state.df_vt.at[idx_vt, 'Tồn Kho VT'] >= vt_sl_xuat:
                                    st.session_state.df_vt.at[idx_vt, 'Đã Xuất'] += vt_sl_xuat
                                    log_noi_xuat = f" | Nơi xuất: {vt_noi_xuat}" if vt_noi_xuat else ""
                                    log_action("Xuất Vật tư", f"Xuất {vt_sl_xuat} {vt_sel} cho {vt_nguoi}{log_noi_xuat} (CT: {sel_ct_vt})")
                                    save_all()
                                    st.success(f"✅ Đã xuất/cho mượn {vt_sl_xuat} {vt_sel} thành công!")
                                    st.rerun()
                                else:
                                    st.error("❌ Không đủ số lượng trong kho vật tư!")

                with st.expander("🔙 Hoàn trả thiết bị (Thu hồi)", expanded=False):
                    with st.form("tra_vattu"):
                        vt_tra_sel = st.selectbox("Chọn Thiết bị trả lại:", st.session_state.df_vt[st.session_state.df_vt['Phân Loại'] == 'Thiết bị']['Tên Vật Tư'].tolist())
                        vt_sl_tra = st.number_input("Số lượng trả", min_value=1)
                        vt_tt_tra = st.selectbox("Tình trạng lúc trả", ["Bình thường", "Hỏng hóc", "Thất lạc"])
                        
                        if st.form_submit_button("Xác nhận thu hồi"):
                            if not sel_ct_vt:
                                st.error("⚠️ Vui lòng nhập hoặc chọn Tên chương trình trước khi thu hồi!")
                            elif vt_tra_sel:
                                idx_tra = st.session_state.df_vt[st.session_state.df_vt['Tên Vật Tư'] == vt_tra_sel].index[0]
                                st.session_state.df_vt.at[idx_tra, 'Đã Xuất'] -= vt_sl_tra
                                if st.session_state.df_vt.at[idx_tra, 'Đã Xuất'] < 0: 
                                    st.session_state.df_vt.at[idx_tra, 'Đã Xuất'] = 0
                                
                                st.session_state.df_vt.at[idx_tra, 'Tình Trạng'] = vt_tt_tra
                                log_action("Thu hồi Vật tư", f"Thu hồi {vt_sl_tra} {vt_tra_sel} từ CT {sel_ct_vt} - Tình trạng: {vt_tt_tra}")
                                save_all()
                                st.success(f"✅ Đã thu hồi {vt_sl_tra} {vt_tra_sel} thành công!")
                                st.rerun()
            else:
                st.info("Chưa có vật tư nào trong hệ thống để xuất!")

    # ==========================================
    # MODULE 3: QUẢN LÝ HOẠT ĐỘNG
    # ==========================================
    elif main_module == "📅 Quản lý Hoạt Động":
        st.markdown(f"<h2 style='color:{main_color};'>📅 PHÂN HỆ QUẢN LÝ HOẠT ĐỘNG & CHIẾN DỊCH</h2>", unsafe_allow_html=True)
        tabs_hd = st.tabs(["🎯 DANH SÁCH CHƯƠNG TRÌNH", "📝 LẬP DỰ TRÙ HẬU CẦN", "📊 BÁO CÁO TỔNG KẾT"])
        
        with tabs_hd[0]:
            st.subheader("🎨 Quản lý Danh sách Chương trình / Đợt khám")
            with st.expander("➕ Tạo Chương trình/Đợt khám mới", expanded=False):
                with st.form("tao_ct_moi"):
                    new_ct_name = st.text_input("Tên chương trình mới")
                    if st.form_submit_button("Tạo ngay"):
                        if new_ct_name:
                            st.session_state.df_ct = pd.concat([st.session_state.df_ct, pd.DataFrame([{'Tên Chương Trình': new_ct_name, 'Trạng Thái': 'Đang mở'}])], ignore_index=True)
                            log_action("Tạo chương trình", f"Tạo mới {new_ct_name}")
                            save_all(); st.rerun()

            ed_ct = st.data_editor(st.session_state.df_ct, use_container_width=True, hide_index=True, num_rows="dynamic", key="editor_ct")
            if st.button("💾 Lưu Chương trình"):
                st.session_state.df_ct = ed_ct
                log_action("Sửa chương trình", "Cập nhật danh sách")
                save_all(); st.rerun()

        with tabs_hd[1]:
            st.subheader("📝 Dự trù thuốc & Cảnh báo tồn kho")
            
            c_dt1, c_dt2 = st.columns(2)
            with c_dt1:
                st.markdown("**1. Dự trù tổng quát (Kho chung)**")
                with st.form("f_dt_64"):
                    t_dt = st.selectbox("Chọn thuốc:", sorted(st.session_state.df_kho['Tên Biệt Dược'].unique().tolist()) if not st.session_state.df_kho.empty else ["N/A"])
                    sl_dt = st.number_input("Số lượng dự trù", min_value=1)
                    if st.form_submit_button("Thêm dự trù tổng"):
                        new_dt = pd.DataFrame([{'Tên Thuốc': t_dt, 'Số Lượng Dự Trù': sl_dt, 'Chương Trình': 'Kho Tổng'}])
                        st.session_state.df_dt = pd.concat([st.session_state.df_dt, new_dt], ignore_index=True)
                        log_action("Dự trù", f"Dự trù {sl_dt} {t_dt}")
                        save_all(); st.rerun()
            
            with c_dt2:
                st.markdown("**2. Dự trù riêng theo Chương trình**")
                if not st.session_state.df_ct.empty:
                    view_ct = st.selectbox("Chọn chương trình:", st.session_state.df_ct['Tên Chương Trình'].tolist(), key="sel_ct_dt")
                    with st.form("f_dt_rieng"):
                        t_dt_r = st.selectbox("Chọn thuốc:", sorted(st.session_state.df_kho['Tên Biệt Dược'].unique().tolist()) if not st.session_state.df_kho.empty else ["N/A"], key="sel_t_dt_r")
                        sl_dt_r = st.number_input("Số lượng", min_value=1, key="num_sl_dt_r")
                        if st.form_submit_button("Thêm dự trù cho đợt này"):
                            new_dt_r = pd.DataFrame([{'Tên Thuốc': t_dt_r, 'Số Lượng Dự Trù': sl_dt_r, 'Chương Trình': view_ct}])
                            st.session_state.df_dt = pd.concat([st.session_state.df_dt, new_dt_r], ignore_index=True)
                            save_all(); st.rerun()
                else:
                    st.info("Vui lòng tạo chương trình trước!")
            
            st.divider()
            st.markdown("#### 📋 Bảng theo dõi Dự trù vs Tồn kho")
            if not st.session_state.df_dt.empty:
                if 'Chương Trình' not in st.session_state.df_dt.columns: 
                    st.session_state.df_dt['Chương Trình'] = "Kho Tổng"
                
                loc_ct = st.selectbox("Lọc dự trù theo:", ["Tất cả"] + st.session_state.df_dt['Chương Trình'].dropna().unique().tolist())
                df_dt_view = st.session_state.df_dt if loc_ct == "Tất cả" else st.session_state.df_dt[st.session_state.df_dt['Chương Trình'] == loc_ct]
                
                res = df_dt_view.merge(st.session_state.df_kho[['Tên Biệt Dược', 'Tồn Kho']], left_on='Tên Thuốc', right_on='Tên Biệt Dược', how='left').fillna(0)
                res['Thiếu'] = (res['Số Lượng Dự Trù'] - res['Tồn Kho']).clip(lower=0)
                
                if 'Tên Biệt Dược' in res.columns:
                    res = res.drop(columns=['Tên Biệt Dược'])
                    
                def color_row(row): return [f'background-color: {"#ffcccc" if row["Thiếu"] > 0 else "#ccffcc"}'] * len(row)
                st.dataframe(res.style.apply(color_row, axis=1), use_container_width=True)

        with tabs_hd[2]:
            st.subheader("📊 Báo cáo Tổng kết Chiến dịch")
            if not st.session_state.df_ct.empty:
                bc_ct = st.selectbox("🔍 Chọn chương trình để xem báo cáo:", st.session_state.df_ct['Tên Chương Trình'].tolist(), key="bc_ct")
                
                st.markdown(f"**📤 Lịch sử Thuốc đã xuất cho: {bc_ct}**")
                if not st.session_state.df_ls.empty and 'Chương Trình' in st.session_state.df_ls.columns:
                    df_x_ct = st.session_state.df_ls[st.session_state.df_ls['Chương Trình'] == bc_ct]
                else: df_x_ct = pd.DataFrame()
                    
                st.dataframe(df_x_ct, use_container_width=True, hide_index=True)
                
                if not df_x_ct.empty:
                    out_ex = BytesIO()
                    with pd.ExcelWriter(out_ex, engine='xlsxwriter') as writer: 
                        df_x_ct.to_excel(writer, index=False, sheet_name='BaoCaoXuatThuoc')
                    st.download_button(label="📥 Tải Báo Cáo Excel (Lịch Sử Xuất)", data=out_ex.getvalue(), file_name=f"Bao_Cao_Xuat_Thuoc_{bc_ct}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
            else:
                st.info("Chưa có chương trình nào được tạo.")

    # ==========================================
    # MODULE 4: QUẢN LÝ NHÂN SỰ
    # ==========================================
    elif main_module == "👥 Quản lý Nhân Sự":
        st.markdown(f"<h2 style='color:{main_color};'>👥 PHÂN HỆ QUẢN LÝ NHÂN SỰ & BẢO MẬT</h2>", unsafe_allow_html=True)
        col_p, col_m = st.columns([1.5, 2])
        
        with col_p:
            st.markdown("#### 👤 Hồ sơ của bạn")
            idx = st.session_state.df_ns[st.session_state.df_ns['Username'] == st.session_state.u_data['Username']].index[0]
            with st.form("my_profile"):
                nh = st.text_input("Họ tên", value=st.session_state.df_ns.at[idx, 'Họ Tên'] if pd.notna(st.session_state.df_ns.at[idx, 'Họ Tên']) else "")
                nm = st.text_input("MSSV", value=st.session_state.df_ns.at[idx, 'MSSV'] if pd.notna(st.session_state.df_ns.at[idx, 'MSSV']) else "")
                nl = st.text_input("Lớp", value=st.session_state.df_ns.at[idx, 'Lớp'] if pd.notna(st.session_state.df_ns.at[idx, 'Lớp']) else "")
                up_ava = st.file_uploader("📷 Tải lên Avatar mới", type=['png', 'jpg'])
                
                if st.form_submit_button("LƯU HỒ SƠ"):
                    st.session_state.df_ns.at[idx,'Họ Tên'], st.session_state.df_ns.at[idx,'MSSV'], st.session_state.df_ns.at[idx,'Lớp'] = nh, nm, nl
                    if up_ava: Image.open(up_ava).save(os.path.join(FOLDER_AVATAR, f"{st.session_state.u_data['Username']}.png"))
                    log_action("Sửa hồ sơ", "Cập nhật hồ sơ cá nhân")
                    save_all(); st.rerun()
                    
        if st.session_state.u_data.get('Quyền') == 'admin':
            with col_m:
                st.markdown("#### 🔐 Cấp phát tài khoản")
                with st.form("add_acc"):
                    au, ap, an = st.text_input("Username"), st.text_input("Password"), st.text_input("Họ tên SV")
                    am, al = st.text_input("MSSV"), st.text_input("Lớp")
                    if st.form_submit_button("Cấp tài khoản"):
                        st.session_state.df_ns = pd.concat([st.session_state.df_ns, pd.DataFrame([{'Username':au, 'Password':ap, 'Quyền':'user', 'Họ Tên':an, 'MSSV':am, 'Lớp':al}])], ignore_index=True)
                        log_action("Cấp tài khoản", f"Tạo user {au}")
                        save_all(); st.rerun()
                st.data_editor(st.session_state.df_ns, use_container_width=True, key="editor_ns")

            st.divider()
            st.markdown("### 🕵️ NHẬT KÝ HỆ THỐNG (AUDIT TRAIL)")
            if not st.session_state.df_audit.empty:
                st.dataframe(st.session_state.df_audit.sort_index(ascending=False), use_container_width=True)
            else:
                st.info("Chưa có ghi nhận nào.")