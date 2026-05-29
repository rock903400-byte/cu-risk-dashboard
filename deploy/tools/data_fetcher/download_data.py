import urllib.request
import urllib.parse
import urllib.error
import http.cookiejar
import re
import tkinter as tk
from tkinter import simpledialog

def get_credentials():
    root = tk.Tk(); root.withdraw(); root.attributes("-topmost", True)
    class LoginDialog(simpledialog.Dialog):
        def body(self, master):
            self.title("請輸入登入資訊")
            tk.Label(master, text="帳號:").grid(row=0); tk.Label(master, text="密碼:").grid(row=1)
            tk.Label(master, text="起迄年月 (例: 11201-11212):").grid(row=2)
            self.e1 = tk.Entry(master); self.e2 = tk.Entry(master, show="*"); self.e3 = tk.Entry(master)
            self.e1.grid(row=0, column=1); self.e2.grid(row=1, column=1); self.e3.grid(row=2, column=1)
            return self.e1
        def apply(self): self.result = (self.e1.get(), self.e2.get(), self.e3.get())
    dialog = LoginDialog(root); res = dialog.result; root.destroy(); return res

print("Cookieless 狀態自動化測試啟動 (已確認寫入檔案)...")
credentials = get_credentials()
if not credentials: exit()
ACCOUNT, PASSWORD, YM_RANGE = credentials
LOGIN_URL = "http://localhost/ap/audit_cu/PR019.aspx"

cj = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
urllib.request.install_opener(opener)
headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36", "Content-Type": "application/x-www-form-urlencoded"}

def save_debug_html(html, filename):
    """儲存偵錯用的 HTML 檔案"""
    path = f"C:\\Users\\user\\Desktop\\穿透協會\\{filename}"
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"已存檔: {filename}")

def get_aspset_payload_pairs(html, target_button_name=None, target_button_value=None):
    pairs = []
    if target_button_value and not target_button_name:
        btn_match = re.search(r'<input[^>]+name=["\']([^"\']+)["\'][^>]+value=["\']' + re.escape(target_button_value) + r'["\']', html, re.I)
        if btn_match: target_button_name = btn_match.group(1)

    for match in re.finditer(r'<input[^>]*>', html, re.I):
        tag = match.group(0); name_m = re.search(r'name=["\']?([^"\'\s>]+)', tag, re.I)
        type_m = re.search(r'type=["\']?([^"\'\s>]+)', tag, re.I); val_m = re.search(r'value=["\']([^"\']*)["\']', tag, re.I)
        checked = re.search(r'\schecked\b', tag, re.I)
        if not name_m: continue
        name = name_m.group(1); value = val_m.group(1) if val_m else "on"; itype = type_m.group(1).lower() if type_m else "text"
        if itype == "hidden" or name.startswith("__"): pairs.append((name, val_m.group(1) if val_m else ""))
        elif itype == "checkbox" or itype == "radio":
            if checked: pairs.append((name, value))
        elif itype == "submit" or itype == "image":
            if name == target_button_name: pairs.append((name, target_button_value or value))
        else: pairs.append((name, val_m.group(1) if val_m else ""))

    for match in re.finditer(r'<select[^>]*>.*?</select>', html, re.I | re.S):
        select_tag = match.group(0); name_m = re.search(r'name=["\']?([^"\'\s>]+)', select_tag, re.I)
        if not name_m: continue
        name = name_m.group(1); found_any = False
        for opt_match in re.finditer(r'<option[^>]*selected[^>]*value=["\']?([^"\'\s>]+)["\']?', select_tag, re.I):
            pairs.append((name, opt_match.group(1))); found_any = True
        if not found_any and 'multiple' not in select_tag.lower():
            first_val_m = re.search(r'<option[^>]*value=["\']?([^"\'\s>]+)["\']?', select_tag, re.I)
            if first_val_m: pairs.append((name, first_val_m.group(1)))
    if target_button_name:
        pairs = [p for p in pairs if p[0] not in ["__EVENTTARGET", "__EVENTARGUMENT"]]
        pairs.extend([("__EVENTTARGET", ""), ("__EVENTARGUMENT", "")])
    return pairs

def get_aspset_payload_dict(html, target_button_name=None, target_button_value=None):
    return dict(get_aspset_payload_pairs(html, target_button_name, target_button_value))

def get_form_action(html, base_url):
    match = re.search(r'<form[^>]+action=["\']([^"\']+)["\']', html, re.I)
    return urllib.parse.urljoin(base_url, match.group(1)) if match else base_url

def do_postback(opener, url, current_html, target, argument, headers, overrides=None):
    payload = get_aspset_payload_dict(current_html); payload.update({"__EVENTTARGET": target, "__EVENTARGUMENT": argument})
    if overrides: payload.update(overrides)
    with opener.open(urllib.request.Request(url, data=urllib.parse.urlencode(payload).encode(), headers=headers, method='POST')) as res:
        return res.read().decode('utf-8', errors='ignore'), res.geturl()

def click_button(opener, url, current_html, btn_value, headers):
    payload = get_aspset_payload_dict(current_html, None, btn_value)
    with opener.open(urllib.request.Request(url, data=urllib.parse.urlencode(payload).encode(), headers=headers, method='POST')) as res:
        return res.read().decode('utf-8', errors='ignore'), res.geturl()

try:
    print("正在連線...")
    with opener.open(urllib.request.Request(LOGIN_URL, headers=headers)) as res:
        current_html = res.read().decode('utf-8', errors='ignore'); current_url = res.geturl()

    # 登入
    payload = get_aspset_payload_dict(current_html)
    payload.update({"Login_Main$UserName": ACCOUNT, "Login_Main$Password": PASSWORD, "Login_Main$LoginImageButton.x": "30", "Login_Main$LoginImageButton.y": "20"})
    login_headers = headers.copy(); login_headers["Referer"] = current_url
    with opener.open(urllib.request.Request(get_form_action(current_html, current_url), data=urllib.parse.urlencode(payload).encode(), headers=login_headers, method='POST')) as res:
        current_html = res.read().decode('utf-8', errors='ignore'); current_url = res.geturl()
        if "Login_Main" in current_html: print("警告：登入失敗！"); exit()
        print("登入成功！")
    headers["Referer"] = current_url

    # 1. 單位社選擇
    print("\n執行：1.單位社選擇...")
    m = re.search(r"__doPostBack\('([^']+)','([^']*(?:單位社選擇)[^']*)'\)", current_html)
    if m: current_html, current_url = do_postback(opener, get_form_action(current_html, current_url), current_html, m.group(1), m.group(2), headers)
    current_html, current_url = click_button(opener, get_form_action(current_html, current_url), current_html, "全部選取", headers)
    current_html, current_url = click_button(opener, get_form_action(current_html, current_url), current_html, "勾選確認（資料移往下方）", headers)

    # 2. 會科選擇
    print("執行：2.會科選擇 (損益 + 資產負債)...")
    m = re.search(r"__doPostBack\('([^']+)','([^']*(?:會科選擇)[^']*)'\)", current_html)
    if m: current_html, current_url = do_postback(opener, get_form_action(current_html, current_url), current_html, m.group(1), m.group(2), headers)
    for category in ["損益科目", "資產負債科目"]:
        current_html, current_url = click_button(opener, get_form_action(current_html, current_url), current_html, category, headers)
        current_html, current_url = click_button(opener, get_form_action(current_html, current_url), current_html, "全部選取", headers)
        current_html, current_url = click_button(opener, get_form_action(current_html, current_url), current_html, "勾選確認（資料移往下方）", headers)

    # 3. 年月選擇
    print("執行：3.年月選擇...")
    m = re.search(r"__doPostBack\('([^']+)','([^']*(?:年月選擇)[^']*)'\)", current_html)
    if m: current_html, current_url = do_postback(opener, get_form_action(current_html, current_url), current_html, m.group(1), m.group(2), headers)
    s_ym, e_ym = YM_RANGE.split("-") if "-" in YM_RANGE else (YM_RANGE, YM_RANGE)
    ds = re.findall(r'<select[^>]+name=["\'](ctl00\$ContentPlaceHolder1\$DropDownList[^"\']+)["\'][^>]*>(.*?)</select>', current_html, re.I | re.S)
    ovrs = {}
    for i, (name, content) in enumerate(ds):
        if i >= 2: break
        vals = re.findall(r'value=["\']?([^"\'\s>]+)["\']?', content, re.I)
        target = [s_ym, e_ym][i]
        ovrs[name] = target if target in vals else (vals[0] if vals else target)
    current_html, current_url = do_postback(opener, get_form_action(current_html, current_url), current_html, "ctl00$ContentPlaceHolder1$DropDownList1", "", headers, ovrs)

    # 4. 查詢
    print("執行：4.查詢...")
    m = re.search(r"__doPostBack\('([^']+)','([^']*(?:查詢)[^']*)'\)", current_html)
    if m: current_html, current_url = do_postback(opener, get_form_action(current_html, current_url), current_html, m.group(1), m.group(2), headers, ovrs)

    # 最終轉檔
    print("執行：資料轉檔...")
    target_btn = None
    for match in re.finditer(r'<input[^>]+type=["\']submit["\'][^>]*>', current_html, re.I):
        tag = match.group(0); val_m = re.search(r'value=["\']([^"\']*)["\']', tag, re.I)
        if val_m and "資料轉檔(不含累積數)" in val_m.group(1):
            target_btn = re.search(r'name=["\']([^"\']*)["\']', tag, re.I).group(1); break

    if not target_btn: print("錯誤：找不到轉檔按鈕！"); exit()
    payload = get_aspset_payload_dict(current_html, target_btn, "資料轉檔(不含累積數)")
    with opener.open(urllib.request.Request(get_form_action(current_html, current_url), data=urllib.parse.urlencode(payload).encode(), headers=headers, method='POST')) as res:
        raw_data = res.read()
        # 關鍵修正：嘗試多種編碼讀取，並統一存成帶 BOM 的 UTF-8
        text_content = ""
        for encoding in ['utf-8', 'cp950', 'big5']:
            try:
                text_content = raw_data.decode(encoding)
                break
            except: continue
        
        if not text_content: text_content = raw_data.decode('utf-8', errors='ignore')
        
        file_path = "C:\\Users\\user\\Desktop\\穿透協會\\exported_data.csv"
        with open(file_path, "w", encoding="utf-8-sig", newline='') as f:
            f.write(text_content)
        print(f"轉檔完成！檔案已存至 exported_data.csv ({len(raw_data)} bytes)")

except Exception as e: print(f"執行出錯: {e}")
print("執行完畢。")
