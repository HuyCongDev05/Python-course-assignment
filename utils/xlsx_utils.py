import os
import zipfile
from datetime import datetime, timezone
from xml.etree import ElementTree as ET


MAIN_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PACKAGE_REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
CORE_NS = "http://schemas.openxmlformats.org/package/2006/metadata/core-properties"
DC_NS = "http://purl.org/dc/elements/1.1/"
DCTERMS_NS = "http://purl.org/dc/terms/"
DCTERMS_TYPE_NS = "http://purl.org/dc/dcmitype/"
XSI_NS = "http://www.w3.org/2001/XMLSchema-instance"


def _column_index_from_reference(reference):
    column_name = ""
    for character in reference:
        if character.isalpha():
            column_name += character
        else:
            break

    index = 0
    for character in column_name.upper():
        index = index * 26 + (ord(character) - 64)
    return max(index - 1, 0)


def _column_name_from_index(index):
    index += 1
    result = []
    while index > 0:
        index, remainder = divmod(index - 1, 26)
        result.append(chr(65 + remainder))
    return "".join(reversed(result))


def _escape_xml_text(value):
    value = str(value)
    return (
        value.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _shared_string_value(shared_string):
    parts = []
    for node in shared_string.iter():
        if node.tag == f"{{{MAIN_NS}}}t":
            parts.append(node.text or "")
    return "".join(parts)


def _cell_value(cell, shared_strings):
    cell_type = cell.get("t")
    if cell_type == "inlineStr":
        parts = []
        for node in cell.iter():
            if node.tag == f"{{{MAIN_NS}}}t":
                parts.append(node.text or "")
        return "".join(parts)

    value_node = cell.find(f"{{{MAIN_NS}}}v")
    raw_value = value_node.text if value_node is not None else ""

    if cell_type == "s":
        if not raw_value:
            return ""
        return shared_strings[int(raw_value)]
    if cell_type == "b":
        return raw_value == "1"
    if raw_value is None:
        return ""

    raw_value = raw_value.strip()
    if raw_value == "":
        return ""

    if raw_value.isdigit() or (raw_value.startswith("-") and raw_value[1:].isdigit()):
        try:
            return int(raw_value)
        except ValueError:
            return raw_value

    try:
        return float(raw_value)
    except ValueError:
        return raw_value


def _first_sheet_path(archive):
    workbook_tree = ET.fromstring(archive.read("xl/workbook.xml"))
    relationships_tree = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))

    sheet = workbook_tree.find(f".//{{{MAIN_NS}}}sheet")
    if sheet is None:
        raise ValueError("File Excel không có sheet dữ liệu.")

    relation_id = sheet.get(f"{{{REL_NS}}}id")
    if not relation_id:
        raise ValueError("Không xác định được sheet dữ liệu trong file Excel.")

    for relation in relationships_tree.findall(f".//{{{PACKAGE_REL_NS}}}Relationship"):
        if relation.get("Id") == relation_id:
            target = relation.get("Target", "")
            return target.lstrip("/")

    raise ValueError("Không tìm thấy liên kết sheet trong file Excel.")


def read_xlsx_rows(file_path):
    if not os.path.exists(file_path):
        raise ValueError("Không tìm thấy file Excel đã chọn.")

    try:
        with zipfile.ZipFile(file_path, "r") as archive:
            shared_strings = []
            if "xl/sharedStrings.xml" in archive.namelist():
                shared_tree = ET.fromstring(archive.read("xl/sharedStrings.xml"))
                shared_strings = [_shared_string_value(item) for item in shared_tree.findall(f"{{{MAIN_NS}}}si")]

            sheet_path = _first_sheet_path(archive)
            if not sheet_path.startswith("xl/"):
                sheet_path = f"xl/{sheet_path}"

            sheet_tree = ET.fromstring(archive.read(sheet_path))
    except zipfile.BadZipFile as exc:
        raise ValueError("File đã chọn không phải định dạng .xlsx hợp lệ.") from exc
    except KeyError as exc:
        raise ValueError("Cấu trúc file Excel không hợp lệ hoặc bị thiếu dữ liệu.") from exc
    except ET.ParseError as exc:
        raise ValueError("Không đọc được nội dung XML trong file Excel.") from exc

    rows = []
    for row_node in sheet_tree.findall(f".//{{{MAIN_NS}}}sheetData/{{{MAIN_NS}}}row"):
        cells = {}
        max_column = -1
        for cell in row_node.findall(f"{{{MAIN_NS}}}c"):
            reference = cell.get("r", "")
            column_index = _column_index_from_reference(reference) if reference else max_column + 1
            cells[column_index] = _cell_value(cell, shared_strings)
            max_column = max(max_column, column_index)

        row_values = [""] * (max_column + 1 if max_column >= 0 else 0)
        for column_index, value in cells.items():
            row_values[column_index] = value
        rows.append(row_values)

    if not rows:
        return [], []

    headers = [str(value).replace("\ufeff", "").strip() for value in rows[0]]
    return headers, rows[1:]


def write_xlsx(file_path, sheet_name, headers, rows):
    safe_sheet_name = str(sheet_name or "Sheet1").strip()[:31] or "Sheet1"
    safe_sheet_name = safe_sheet_name.translate({ord(char): None for char in '[]:*?/\\'})

    workbook_rows = [list(headers)] + [list(row) for row in rows]
    last_column_name = _column_name_from_index(max(len(headers) - 1, 0))
    last_row_index = max(len(workbook_rows), 1)
    dimension = f"A1:{last_column_name}{last_row_index}"

    sheet_rows_xml = []
    for row_index, row in enumerate(workbook_rows, start=1):
        cells_xml = []
        for column_index, value in enumerate(row):
            if value is None or value == "":
                continue
            reference = f"{_column_name_from_index(column_index)}{row_index}"
            escaped_value = _escape_xml_text(value)
            cells_xml.append(
                f'<c r="{reference}" t="inlineStr"><is><t>{escaped_value}</t></is></c>'
            )
        sheet_rows_xml.append(f'<row r="{row_index}">{"".join(cells_xml)}</row>')

    created_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()

    content_types_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
  <Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
  <Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>
  <Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>
</Types>
"""

    root_relationships_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>
  <Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/>
</Relationships>
"""

    workbook_xml = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<workbook xmlns="{MAIN_NS}" xmlns:r="{REL_NS}">
  <sheets>
    <sheet name="{_escape_xml_text(safe_sheet_name)}" sheetId="1" r:id="rId1"/>
  </sheets>
</workbook>
"""

    workbook_relationships_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>
</Relationships>
"""

    worksheet_xml = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<worksheet xmlns="{MAIN_NS}">
  <dimension ref="{dimension}"/>
  <sheetViews>
    <sheetView workbookViewId="0"/>
  </sheetViews>
  <sheetFormatPr defaultRowHeight="15"/>
  <sheetData>
    {"".join(sheet_rows_xml)}
  </sheetData>
</worksheet>
"""

    core_xml = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<cp:coreProperties xmlns:cp="{CORE_NS}" xmlns:dc="{DC_NS}" xmlns:dcterms="{DCTERMS_NS}" xmlns:dcmitype="{DCTERMS_TYPE_NS}" xmlns:xsi="{XSI_NS}">
  <dc:creator>DormManager</dc:creator>
  <cp:lastModifiedBy>DormManager</cp:lastModifiedBy>
  <dcterms:created xsi:type="dcterms:W3CDTF">{created_at}</dcterms:created>
  <dcterms:modified xsi:type="dcterms:W3CDTF">{created_at}</dcterms:modified>
</cp:coreProperties>
"""

    app_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties" xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes">
  <Application>DormManager</Application>
</Properties>
"""

    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with zipfile.ZipFile(file_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", content_types_xml)
        archive.writestr("_rels/.rels", root_relationships_xml)
        archive.writestr("xl/workbook.xml", workbook_xml)
        archive.writestr("xl/_rels/workbook.xml.rels", workbook_relationships_xml)
        archive.writestr("xl/worksheets/sheet1.xml", worksheet_xml)
        archive.writestr("docProps/core.xml", core_xml)
        archive.writestr("docProps/app.xml", app_xml)
