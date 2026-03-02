from telegram import Update
from telegram.ext import ContextTypes
from datetime import datetime
import re
from app.services.google_services import client, drive
from app.keyboards import *
from app.utils import safe_upper, safe_label
from app.config import CREDS
from app.config import (
    USER_MANAGEMENT_ID,
    STO_MAPPING,
    KET_DEFAULT,
    BULAN_ID,
    DRIVE_ROOT_DATA,
    DRIVE_ROOT_FOTO
)

from telegram import ReplyKeyboardMarkup


user_sheet = client.open_by_key(USER_MANAGEMENT_ID).worksheet("USERS")

def delete_drive_file_from_cell(cell_value):
    try:
        match = re.search(r'/d/([a-zA-Z0-9_-]+)', cell_value)
        if not match:
            print("Tidak ada file ID")
            return False

        file_id = match.group(1)
        print("Coba hapus file:", file_id)

        drive.files().delete(fileId=file_id).execute()

        print("BERHASIL DIHAPUS")
        return True

    except Exception as e:
        print("ERROR DELETE:", e)
        return False

def get_formula_cell(ws, row, col):
    return ws.get_values(
        f"A{row}:ZZ{row}",
        value_render_option="FORMULA"
    )[0][col-1]
    
def get_gamas_dashboard():
    
    current_year = datetime.now().year
    years = [current_year-1, current_year, current_year+1]

    total_all = 0
    total_per_year = {}
    total_per_sto = {"BBU":0,"WNC":0,"UNH":0}
    per_sheet_data = {}

    for year in years:
        try:
            sheet_id = get_year_spreadsheet(year)
            master = client.open_by_key(sheet_id)

            total_year = 0

            for ws in master.worksheets():

                rows = ws.get_all_values()
                if len(rows) <= 1:
                    continue

                sheet_name = ws.title
                count = len(rows) - 1

                total_year += count
                total_all += count

                if sheet_name not in per_sheet_data:
                    per_sheet_data[sheet_name] = {
                        "total": 0,
                        "bulan": {},
                        "dates": []
                    }

                per_sheet_data[sheet_name]["total"] += count

                for r in rows[1:]:

                    sto = r[1]
                    if sto in total_per_sto:
                        total_per_sto[sto] += 1

                    bulan = r[9]
                    if bulan:
                        per_sheet_data[sheet_name]["bulan"][bulan] = \
                            per_sheet_data[sheet_name]["bulan"].get(bulan,0) + 1

                    try:
                        d = datetime.strptime(r[4], "%d/%m/%Y")
                        per_sheet_data[sheet_name]["dates"].append(d)
                    except:
                        pass

            if total_year > 0:
                total_per_year[year] = total_year

        except:
            continue

    return total_all, total_per_year, total_per_sto, per_sheet_data

# ================= USER MANAGEMENT =================
def renumber_users():
    data = user_sheet.get_all_values()
    for i in range(2, len(data)+1):
        user_sheet.update_cell(i, 1, i-1)


def get_user(user_id):
    users = user_sheet.get_all_values()
    for i in range(1, len(users)):
        if users[i][1] == str(user_id):
            return {
                "row": i+1,
                "nama": users[i][2],
                "role": users[i][4],
                "status": users[i][5]
            }
    return None


def add_user(user_id, nama, telp):
    today = datetime.now().strftime("%d/%m/%Y")
    user_sheet.append_row([
        "",
        str(user_id),
        safe_upper(nama),
        telp,
        "TEKNISI",
        "PENDING",
        today
    ])
    renumber_users()


def update_status(user_id, status):
    user = get_user(user_id)
    if user:
        user_sheet.update_cell(user["row"], 6, status)
        return True
    return False


def check_access(update):
    user = get_user(update.effective_user.id)

    if not user:
        return "NOT_REGISTERED"

    if user["status"] == "PENDING":
        return "PENDING"

    if user["status"] == "NONAKTIF":
        return "NONAKTIF"

    if user["status"] == "AKTIF":
        return user["role"]

    return "INVALID"
# ================= DRIVE ENGINE =================

def get_folder(name, parent):
    query = f"name='{name}' and '{parent}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false"
    result = drive.files().list(q=query, fields="files(id)").execute()

    if result["files"]:
        return result["files"][0]["id"]

    folder = drive.files().create(
        body={
            "name": name,
            "mimeType": "application/vnd.google-apps.folder",
            "parents": [parent]
        },
        fields="id"
    ).execute()

    return folder["id"]


def get_year_folder_data(year):
    return get_folder(f"01_GAMAS_{year}", DRIVE_ROOT_DATA)


def get_year_folder_foto(year):
    return get_folder(f"01_GAMAS_{year}", DRIVE_ROOT_FOTO)


def get_year_spreadsheet(year):

    folder_id = get_year_folder_data(year)
    title = f"GAMAS_{year}"

    files = drive.files().list(
        q=f"name='{title}' and '{folder_id}' in parents and mimeType='application/vnd.google-apps.spreadsheet' and trashed=false",
        fields="files(id)"
    ).execute()

    if files["files"]:
        return files["files"][0]["id"]

    # create spreadsheet
    file = drive.files().create(
        body={
            "name": title,
            "mimeType": "application/vnd.google-apps.spreadsheet",
            "parents": [folder_id]
        },
        fields="id"
    ).execute()

    sheet_id = file["id"]

    # beri akses service account
    drive.permissions().create(
        fileId=sheet_id,
        body={
            "type": "user",
            "role": "writer",
            "emailAddress": CREDS.service_account_email
        }
    ).execute()

    # buat sheet default
    master_year = client.open_by_key(sheet_id)

    # Sheet 1
    ws1 = master_year.add_worksheet(title="GAMAS BAU BAU", rows=1000, cols=50)
    ws1.append_row([
        "NO","STO","NOMOR TIKET",
        "CATUAN/ NAMA GAMAS (NAMA ODP / ODC / OLT)",
        "REPORTED DATE",
        "JASA",
        "KETERANGAN",
        "PIC (NAMA PENGAMBIL)",
        "NAMA MITRA",
        "BULAN"
    ])

    # Sheet 2
    ws2 = master_year.add_worksheet(title="FMP UNAAHA", rows=1000, cols=50)
    ws2.append_row([
        "NO","STO","NOMOR TIKET",
        "CATUAN/ NAMA GAMAS (NAMA ODP / ODC / OLT)",
        "REPORTED DATE",
        "JASA",
        "KETERANGAN",
        "PIC (NAMA PENGAMBIL)",
        "NAMA MITRA",
        "BULAN"
    ])

    # hapus Sheet1 default bawaan
    try:
        master_year.del_worksheet(master_year.worksheet("Sheet1"))
    except:
        pass

    return sheet_id


# ================= INSERT SORTED =================
def insert_sorted(ws, row_data, date_value):

    rows = ws.get_all_values()
    insert_position = len(rows) + 1

    for i in range(2, len(rows)+1):
        try:
            existing_date = datetime.strptime(ws.cell(i,5).value,"%d/%m/%Y")
            if date_value < existing_date:
                insert_position = i
                break
        except:
            continue

    ws.insert_row(row_data, insert_position)

    # renumber NO
    data = ws.get_all_values()
    for i in range(2, len(data)+1):
        ws.update_cell(i,1,i-1)


# ================= FIND TIKET LINTAS TAHUN =================
def find_ticket_global(ticket):
    
    ticket = safe_upper(ticket)

    #ambil 3 tahun terakhir termasuk tahun depan
    current_year = datetime.now().year
    years = [current_year-1, current_year, current_year+1]

    for year in years:

        try:
            sheet_id = get_year_spreadsheet(year)
            master_year = client.open_by_key(sheet_id)

            for ws in master_year.worksheets():

                headers = [h.strip().upper() for h in ws.row_values(1)]

                if "NOMOR TIKET" not in headers:
                    continue

                col = headers.index("NOMOR TIKET") + 1
                values = ws.col_values(col)

                for i, v in enumerate(values):
                    if safe_upper(v) == ticket:
                        return ws, i+1, year

        except:
            continue

    return None, None, None

# ================= FOTO LIST DINAMIS =================
def foto_list(ws, row):
    
    # Ambil FORMULA asli, bukan value render
    row_data = ws.get_values(
        f"A{row}:ZZ{row}",
        value_render_option="FORMULA"
    )[0]

    fotos = []
    col = 11

    while col <= len(row_data):

        cell_value = row_data[col-1]

        if cell_value and "HYPERLINK" in cell_value:
            try:
                parts = cell_value.split('"')
                label = parts[-2]
                fotos.append((col, label))
            except:
                pass

        col += 1

    return fotos

def find_empty_foto_col(ws,row):

    row_data = ws.row_values(row)
    col = 11

    while True:
        if col > len(row_data) or not row_data[col-1]:
            return col
        col += 1
# ================= MENU =================
def admin_menu():
    return ReplyKeyboardMarkup(
        [
            ["📊 Dashboard User"],
            ["📊 Dashboard GAMAS"],
            ["👥 Kelola User"],
            ["📋 List Pending"],
            ["🔙 KEMBALI"]
        ],
        resize_keyboard=True
    )
    
def main_menu():
    return ReplyKeyboardMarkup(
        [["📝 Input Laporan","📸 Upload Foto"],
         ["🔙 KEMBALI"]],
        resize_keyboard=True
    )

def sto_menu():
    return ReplyKeyboardMarkup(
        [["BBU","WNC","UNH"],
         ["🔙 KEMBALI"]],
        resize_keyboard=True
    )



def preview_menu():
    return ReplyKeyboardMarkup(
        [["💾 SIMPAN"],
         ["❌ BATAL"],
         ["🔙 KEMBALI"]],
        resize_keyboard=True
    )

def foto_menu():
    return ReplyKeyboardMarkup(
        [["➕ TAMBAH FOTO"],
         ["✅ SELESAI"],
         ["🔙 KEMBALI"]],
        resize_keyboard=True
    )
def ket_menu():
    return ReplyKeyboardMarkup(
        [["GAMAS BESAR","GAMAS KECIL"],
         ["INFRA CARE","LAINNYA"],
         ["🔙 KEMBALI"]],
        resize_keyboard=True
    )


# ================= PREVIEW BUILDER =================
def build_preview(d):
    
    tanggal = d["DATE"].strftime("%d/%m/%Y")

    return f"""
📋 PREVIEW LAPORAN

INC : {d['INC']}   /edit_inc
PIC : {d['PIC']}   /edit_pic
Tanggal : {tanggal}   /edit_date
STO : {d['STO']}   /edit_sto
Catuan : {d['LOC']}   /edit_loc
Jasa : {d['JASA']}   /edit_jasa
Keterangan : {d['KET']}   /edit_ket

Klik 💾 SIMPAN jika sudah benar
"""

# ================= TEXT HANDLER =================
async def text(update:Update,context:ContextTypes.DEFAULT_TYPE):

    msg = update.message.text.strip()

    # ===== GLOBAL BACK =====
    
    if msg == "🔙 KEMBALI":
        context.user_data.clear()

        role = check_access(update)

        if role == "ADMIN":
            await update.message.reply_text("Kembali ke menu admin.", reply_markup=admin_menu())
        else:
            await update.message.reply_text("Kembali ke menu utama.", reply_markup=main_menu())
        return
    # ===== REGISTRASI =====
    if context.user_data.get("mode")=="REG_NAMA":
        context.user_data["reg_nama"]=safe_upper(msg)
        context.user_data["mode"]="REG_TELP"
        await update.message.reply_text("Masukkan Nomor Telepon:")
        return

    if context.user_data.get("mode")=="REG_TELP":
        add_user(update.effective_user.id,context.user_data["reg_nama"],msg)
        context.user_data.clear()
        await update.message.reply_text("✅ Registrasi berhasil. Status: PENDING.\nHubungi admin.")
        return

    # ===== ACCESS CONTROL =====
    access = check_access(update)

    if access == "NOT_REGISTERED":
        context.user_data.clear()
        context.user_data["mode"] = "REG_NAMA"
        await update.message.reply_text("👋 Anda belum terdaftar.\nMasukkan Nama Lengkap:")
        return

    if access == "PENDING":
        await update.message.reply_text("⏳ Akun Anda masih menunggu persetujuan admin.")
        return

    if access == "NONAKTIF":
        await update.message.reply_text("🚫 Akun Anda tidak aktif.")
        return


    # ===== INPUT LAPORAN =====
    if msg=="📝 Input Laporan":
        context.user_data.clear()
        context.user_data["mode"]="INPUT_PIC"
        await update.message.reply_text("Masukkan Nama PIC:")
        return

    if context.user_data.get("mode")=="INPUT_PIC":
        context.user_data["PIC"]=safe_upper(msg)
        context.user_data["mode"]="INPUT_DATE"
        await update.message.reply_text("Masukkan Tanggal (dd/mm/yyyy):")
        return

    if context.user_data.get("mode")=="INPUT_DATE":
        try:
            d=datetime.strptime(msg,"%d/%m/%Y")
            if d>datetime.now():
                await update.message.reply_text("❌ Tanggal tidak boleh melebihi hari ini")
                return
            context.user_data["DATE"]=d
            context.user_data["mode"]="INPUT_INC"
            await update.message.reply_text("Masukkan Nomor Tiket:")
        except:
            await update.message.reply_text("❌ Format salah. Gunakan dd/mm/yyyy")
        return

    if context.user_data.get("mode")=="INPUT_INC":

        ws,row,y=find_ticket_global(msg)
        if ws:
            await update.message.reply_text("❌ Nomor tiket sudah ada.")
            return

        context.user_data["INC"]=safe_upper(msg)
        context.user_data["mode"]="INPUT_STO"
        await update.message.reply_text("Pilih STO:",reply_markup=sto_menu())
        return

    if context.user_data.get("mode")=="INPUT_STO":
        if msg not in STO_MAPPING:
            await update.message.reply_text("❌ Pilih STO dari tombol.")
            return

        context.user_data["STO"]=msg
        context.user_data["mode"]="INPUT_LOC"
        await update.message.reply_text("Masukkan Catuan / Nama GAMAS:")
        return

    if context.user_data.get("mode")=="INPUT_LOC":
        context.user_data["LOC"]=safe_upper(msg)
        context.user_data["mode"]="INPUT_JASA"
        await update.message.reply_text("Masukkan Jasa / Material:")
        return

    if context.user_data.get("mode")=="INPUT_JASA":
        context.user_data["JASA"]=safe_upper(msg)
        context.user_data["mode"]="INPUT_KET"
        await update.message.reply_text("Pilih Keterangan:",reply_markup=ket_menu())
        return

    if context.user_data.get("mode")=="INPUT_KET":
        
        if msg == "LAINNYA":
            context.user_data["mode"]="INPUT_KET_MANUAL"
            await update.message.reply_text("Masukkan Keterangan lainnya:")
            return

        if msg not in KET_DEFAULT:
            await update.message.reply_text("❌ Pilih dari tombol.")
            return

        context.user_data["KET"]=safe_upper(msg)
        context.user_data["mode"]="PREVIEW"
        await update.message.reply_text(build_preview(context.user_data),reply_markup=preview_menu())
        return
    
    if context.user_data.get("mode")=="INPUT_KET_MANUAL":
        context.user_data["KET"]=safe_upper(msg)
        context.user_data["mode"]="PREVIEW"
        await update.message.reply_text(build_preview(context.user_data),reply_markup=preview_menu())
        return

    # ===== EDIT SYSTEM FINAL =====

    # ===== TRIGGER EDIT =====
    if msg.startswith("/edit_") and context.user_data.get("mode") == "PREVIEW":

        field = msg.replace("/edit_", "").upper()

        if field not in ["INC", "PIC", "DATE", "STO", "LOC", "JASA", "KET"]:
            await update.message.reply_text("Field tidak dikenali.")
            return

        context.user_data["edit_field"] = field

        # STO (hybrid tombol)
        if field == "STO":
            context.user_data["mode"] = "EDIT_STO"
            await update.message.reply_text(
                "Pilih STO baru:",
                reply_markup=sto_menu()
            )
            return

        # KET (hybrid tombol + lainnya)
        if field == "KET":
            context.user_data["mode"] = "EDIT_KET"
            await update.message.reply_text(
                "Pilih Keterangan baru:",
                reply_markup=ket_menu()
            )
            return

        # DATE (format khusus)
        if field == "DATE":
            context.user_data["mode"] = "EDIT_DATE"
            await update.message.reply_text(
                "Masukkan tanggal baru (dd/mm/yyyy):"
            )
            return

        # Field biasa
        context.user_data["mode"] = "WAIT_EDIT"
        await update.message.reply_text(
            f"Masukkan nilai baru untuk {field}:"
        )
        return


    # ===== HANDLE EDIT STO =====
    if context.user_data.get("mode") == "EDIT_STO":

        if msg not in STO_MAPPING:
            await update.message.reply_text("❌ Pilih STO dari tombol.")
            return

        context.user_data["STO"] = msg
        context.user_data["mode"] = "PREVIEW"

        await update.message.reply_text(
            build_preview(context.user_data),
            reply_markup=preview_menu()
        )
        return


    # ===== HANDLE EDIT KET =====
    if context.user_data.get("mode") == "EDIT_KET":

        if msg == "LAINNYA":
            context.user_data["mode"] = "EDIT_KET_MANUAL"
            await update.message.reply_text(
                "Masukkan Keterangan baru:"
            )
            return

        if msg not in KET_DEFAULT:
            await update.message.reply_text("❌ Pilih dari tombol.")
            return

        context.user_data["KET"] = safe_upper(msg)
        context.user_data["mode"] = "PREVIEW"

        await update.message.reply_text(
            build_preview(context.user_data),
            reply_markup=preview_menu()
        )
        return


    # ===== HANDLE EDIT KET MANUAL =====
    if context.user_data.get("mode") == "EDIT_KET_MANUAL":

        context.user_data["KET"] = safe_upper(msg)
        context.user_data["mode"] = "PREVIEW"

        await update.message.reply_text(
            build_preview(context.user_data),
            reply_markup=preview_menu()
        )
        return


    # ===== HANDLE EDIT DATE =====
    if context.user_data.get("mode") == "EDIT_DATE":

        try:
            d = datetime.strptime(msg, "%d/%m/%Y")
            context.user_data["DATE"] = d
            context.user_data["mode"] = "PREVIEW"

            await update.message.reply_text(
                build_preview(context.user_data),
                reply_markup=preview_menu()
            )
        except:
            await update.message.reply_text(
                "Format salah. Gunakan dd/mm/yyyy"
            )
        return


    # ===== HANDLE EDIT FIELD BIASA =====
    if context.user_data.get("mode") == "WAIT_EDIT":

        field = context.user_data["edit_field"]
        context.user_data[field] = safe_upper(msg)
        context.user_data["mode"] = "PREVIEW"

        await update.message.reply_text(
            build_preview(context.user_data),
            reply_markup=preview_menu()
        )
        return

    # ===== SIMPAN =====
    if msg=="💾 SIMPAN" and context.user_data.get("mode")=="PREVIEW":

        d=context.user_data
        year=d["DATE"].year

        sheet_id=get_year_spreadsheet(year)
        master_year=client.open_by_key(sheet_id)

        sheet_name=STO_MAPPING[d["STO"]]["sheet"]
        mitra=STO_MAPPING[d["STO"]]["mitra"]

        ws=master_year.worksheet(sheet_name)

        row=[
            "",
            d["STO"],
            d["INC"],
            d["LOC"],
            d["DATE"].strftime("%d/%m/%Y"),
            d["JASA"],
            d["KET"],
            d["PIC"],
            mitra,
            BULAN_ID[d["DATE"].month]
        ]

        insert_sorted(ws,row,d["DATE"])

        context.user_data.clear()
        await update.message.reply_text("✅ Laporan tersimpan.",reply_markup=main_menu())
        return

    if msg=="❌ BATAL":
        context.user_data.clear()
        await update.message.reply_text("Input dibatalkan.",reply_markup=main_menu())
        return
    
    # ===== MULAI UPLOAD FOTO =====
    if msg == "📸 Upload Foto":
        context.user_data.clear()
        context.user_data["mode"] = "UPLOAD_INC"
        await update.message.reply_text("Masukkan Nomor Tiket:")
        return

    if context.user_data.get("mode") == "UPLOAD_INC":
        ws,row,year = find_ticket_global(msg)

        if not ws:
            await update.message.reply_text("❌ Nomor tiket tidak ditemukan.")
            return

        context.user_data["INC"] = safe_upper(msg)
        context.user_data["mode"] = "UPLOAD_LABEL"
        await update.message.reply_text("Masukkan Label Foto:")
        return

    if context.user_data.get("mode") == "UPLOAD_LABEL":
        context.user_data["label"] = safe_label(msg)
        context.user_data["mode"] = "WAIT_FOTO"
        await update.message.reply_text("Kirim foto sekarang.")
        return
    
    if msg=="➕ TAMBAH FOTO":
        context.user_data["mode"]="UPLOAD_LABEL"
        await update.message.reply_text("Masukkan Label Foto:")
        return

    if msg=="✅ SELESAI":
        context.user_data.clear()
        await update.message.reply_text("Upload selesai.",reply_markup=main_menu())
        return
    
   
    # ===== FOTO LIST EDIT / HAPUS =====
    if msg.startswith("/hapus") and msg[6:].isdigit():

        if "INC" not in context.user_data:
            await update.message.reply_text(
                "❌ Sesi upload tidak aktif. Silakan mulai ulang dari menu Upload Foto."
            )
            return

        idx = int(msg.replace("/hapus",""))

        ws, row, year = find_ticket_global(context.user_data["INC"])

        if not ws:
            await update.message.reply_text("❌ Data tiket tidak ditemukan.")
            return

        fotos = foto_list(ws, row)

        if 1 <= idx <= len(fotos):
            col = fotos[idx-1][0]

            # ambil isi cell (label + link)
            cell_value = get_formula_cell(ws, row, col)

            # hapus file dari drive jika ada
            if cell_value:
                delete_drive_file_from_cell(cell_value)

            # kosongkan cell spreadsheet
            ws.update_cell(row, col, "")

        else:
            await update.message.reply_text("❌ Nomor foto tidak valid.")
            return

        fotos = foto_list(ws, row)

        text = "📸 Foto Saat Ini:\n"
        for i,(c,label) in enumerate(fotos,1):
            text += f"{i}. {label}  /edit{i} /hapus{i}\n"

        if not fotos:
            text += "Belum ada.\n"

        await update.message.reply_text(text, reply_markup=foto_menu())
        return


    if msg.startswith("/edit") and msg[5:].isdigit():
    
        if "INC" not in context.user_data:
            await update.message.reply_text(
                "❌ Sesi upload tidak aktif. Silakan mulai ulang dari Upload Foto."
            )
            return

        idx = int(msg.replace("/edit",""))

        ws,row,year = find_ticket_global(context.user_data.get("INC",""))
        if not ws:
            await update.message.reply_text("❌ Data tidak ditemukan.")
            return

        fotos = foto_list(ws,row)

        if 1 <= idx <= len(fotos):
            context.user_data["edit_foto_col"] = fotos[idx-1][0]
            context.user_data["mode"] = "EDIT_FOTO_LABEL"
            await update.message.reply_text("Masukkan label baru untuk foto ini:")
        return


    if context.user_data.get("mode") == "EDIT_FOTO_LABEL":
        context.user_data["label"] = safe_label(msg)
        context.user_data["mode"] = "WAIT_EDIT_FOTO"
        await update.message.reply_text("Kirim foto baru sekarang.")
        return
    # ===== DASHBOARD ADMIN =====
    if msg=="📊 Dashboard User" and check_access(update)=="ADMIN":

        users=user_sheet.get_all_values()
        total=len(users)-1

        aktif=0
        pending=0
        nonaktif=0

        for i in range(1,len(users)):
            status=users[i][5]
            if status=="AKTIF":
                aktif+=1
            elif status=="PENDING":
                pending+=1
            elif status=="NONAKTIF":
                nonaktif+=1

        text=f"""
    📊 DASHBOARD USER

    Total User : {total}
    AKTIF : {aktif}
    PENDING : {pending}
    NONAKTIF : {nonaktif}
    """
        await update.message.reply_text(text,reply_markup=admin_menu())
        return
    
    if msg == "📊 Dashboard GAMAS" and check_access(update) == "ADMIN":
    
        total_all, total_per_year, total_per_sto, per_sheet_data = get_gamas_dashboard()

        text = "📊 DASHBOARD GAMAS PRO\n\n"
        text += f"Total Semua Laporan : {total_all}\n\n"

        for y, t in total_per_year.items():
            text += f"📅 Tahun {y} : {t}\n"

        text += "\n📍 Per STO:\n"
        for sto, t in total_per_sto.items():
            text += f"{sto} : {t}\n"

        text += "\n📂 Per Sheet:\n\n"

        for sheet_name, data in per_sheet_data.items():

            text += f"🔹 {sheet_name}\n"
            text += f"Total : {data['total']}\n"

            if data["dates"]:
                start = min(data["dates"]).strftime("%d/%m/%Y")
                end = max(data["dates"]).strftime("%d/%m/%Y")
                text += f"Rentang : {start} s/d {end}\n"

            for bulan, jumlah in data["bulan"].items():
                text += f"{bulan} : {jumlah}\n"

            text += "\n"

        await update.message.reply_text(text, reply_markup=admin_menu())
        return

    if msg == "👥 Kelola User" and check_access(update) == "ADMIN":
    
        users = user_sheet.get_all_values()
        text = "👥 DAFTAR USER:\n\n"

        for i in range(1, len(users)):
            text += f"{users[i][1]} - {users[i][2]} ({users[i][5]})\n"

        text += "\nKetik TELEGRAM ID user untuk ubah status."

        context.user_data["mode"] = "ADMIN_SELECT_USER"

        await update.message.reply_text(text, reply_markup=admin_menu())
        return
    
    if msg=="📋 List Pending" and check_access(update)=="ADMIN":

        users=user_sheet.get_all_values()
        text="📋 USER PENDING:\n\n"

        found=False
        for i in range(1,len(users)):
            if users[i][5]=="PENDING":
                found=True
                text+=f"{users[i][1]} - {users[i][2]}\n"

        if not found:
            text+="Tidak ada."

        await update.message.reply_text(text,reply_markup=admin_menu())
        return
    
    
    if context.user_data.get("mode") == "ADMIN_SELECT_USER":
    
        user_id = msg.strip()
        user = get_user(user_id)

        if not user:
            await update.message.reply_text("❌ User tidak ditemukan.")
            return

        context.user_data["target_user"] = user_id
        context.user_data["mode"] = "ADMIN_SET_STATUS"

        keyboard = ReplyKeyboardMarkup(
            [["AKTIF","NONAKTIF","PENDING"],
            ["🔙 KEMBALI"]],
            resize_keyboard=True
        )

        await update.message.reply_text(
            f"Pilih status baru untuk {user['nama']}:",
            reply_markup=keyboard
        )
        return
    
    if context.user_data.get("mode") == "ADMIN_SET_STATUS":
    
        if msg not in ["AKTIF","NONAKTIF","PENDING"]:
            await update.message.reply_text("❌ Pilih dari tombol.")
            return

        target_id = context.user_data["target_user"]

        if update_status(target_id, msg):
            await update.message.reply_text(
                f"✅ Status berhasil diubah menjadi {msg}.",
                reply_markup=admin_menu()
            )
        else:
            await update.message.reply_text("❌ Gagal update.")

        context.user_data.clear()
        return
        


