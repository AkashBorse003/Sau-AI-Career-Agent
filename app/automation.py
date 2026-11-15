from urllib.parse import urlparse
from playwright.sync_api import sync_playwright
_playwright=None; _browser=None
def inspect_and_fill(url,candidate,resume_path=None):
    global _playwright,_browser
    parsed=urlparse(url)
    if parsed.scheme not in ("http","https") or not parsed.netloc: raise ValueError("Enter a valid http or https URL.")
    if _playwright is None: _playwright=sync_playwright().start()
    if _browser is None or not _browser.is_connected(): _browser=_playwright.chromium.launch(headless=False)
    page=_browser.new_page(); page.goto(url,wait_until="domcontentloaded",timeout=45000); page.wait_for_timeout(1000)
    locator=page.locator("input:not([type=hidden]),textarea,select"); found=[]
    mapping=[
      (["first name","firstname","given-name"],candidate.get("first_name") or (candidate.get("full_name","").split(" ")[0] if candidate.get("full_name") else "")),
      (["last name","lastname","family-name"],candidate.get("last_name") or " ".join(candidate.get("full_name","").split(" ")[1:])),
      (["full name","fullname","your name"],candidate.get("full_name","")), (["email"],candidate.get("email","")),
      (["phone","mobile","tel"],candidate.get("phone","")), (["city","location"],candidate.get("location","")),
      (["linkedin"],candidate.get("linkedin","")), (["github"],candidate.get("github","")), (["website","portfolio"],candidate.get("portfolio",""))]
    for i in range(min(locator.count(),100)):
        field=locator.nth(i)
        try:
            info=field.evaluate("""el=>({tag:el.tagName.toLowerCase(),type:(el.type||'').toLowerCase(),name:el.name||'',id:el.id||'',placeholder:el.placeholder||'',label:(el.labels&&el.labels.length?el.labels[0].innerText:'')||'',required:!!el.required})""")
            found.append(info); hint=" ".join([info.get(k,"") for k in ("name","id","placeholder","label")]).lower()
            if info["type"]=="file" and resume_path: field.set_input_files(resume_path,timeout=1500)
            elif info["type"] not in ("checkbox","radio","submit","button","password","file"):
                for keys,value in mapping:
                    if value and any(k in hint for k in keys): field.fill(str(value),timeout=1500); break
        except Exception: pass
    return {"url":url,"title":page.title(),"fields_found":found,"fields_count":len(found),"message":"Visible browser opened and matching fields filled. Review and submit manually."}
def close_browser():
    global _browser,_playwright
    if _browser: _browser.close(); _browser=None
    if _playwright: _playwright.stop(); _playwright=None
