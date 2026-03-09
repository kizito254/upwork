import csv
from pathlib import Path

DATA_DIR = Path('data')

MAPPINGS = [
    ('customer_contacts.csv', 'DataEntry_Sample_Customers.pdf', 'Customer Contacts Dataset'),
    ('product_inventory.csv', 'DataEntry_Sample_Inventory.pdf', 'Product Inventory Dataset'),
    ('business_leads.csv', 'DataEntry_Sample_Leads.pdf', 'Business Leads Dataset'),
    ('employees_hr.csv', 'DataEntry_Sample_Employees.pdf', 'Employee HR Dataset'),
    ('sales_transactions.csv', 'DataEntry_Sample_Sales.pdf', 'Sales Transactions Dataset'),
]


def escape_pdf_text(value: str) -> str:
    return value.replace('\\', r'\\').replace('(', r'\(').replace(')', r'\)')


def pad_row(row, widths):
    return ' | '.join(str(cell)[:w].ljust(w) for cell, w in zip(row, widths))


def build_lines(csv_path: Path, title: str):
    with csv_path.open(newline='', encoding='utf-8') as f:
        rows = list(csv.reader(f))

    header = rows[0]
    data_rows = rows[1:]

    widths = []
    for i, col in enumerate(header):
        max_len = len(col)
        for row in data_rows[:300]:
            if i < len(row):
                max_len = max(max_len, len(str(row[i])))
        widths.append(min(max_len, 24))

    sep = '-+-'.join('-' * w for w in widths)
    lines = [title, '', pad_row(header, widths), sep]
    for row in data_rows:
        lines.append(pad_row(row, widths))

    return lines


def write_simple_text_pdf(output_path: Path, lines):
    page_width = 612
    page_height = 792
    margin_left = 40
    margin_top = 50
    font_size = 10
    leading = 14
    max_lines_per_page = (page_height - margin_top * 2) // leading

    pages = [lines[i:i + max_lines_per_page] for i in range(0, len(lines), max_lines_per_page)]

    objects = []

    # 1: Catalog
    objects.append('<< /Type /Catalog /Pages 2 0 R >>')

    # 2: Pages (kids filled later)
    objects.append(None)

    # 3: Font
    objects.append('<< /Type /Font /Subtype /Type1 /BaseFont /Courier >>')

    page_object_numbers = []
    content_object_numbers = []

    for page_lines in pages:
        content_cmds = ['BT', f'/F1 {font_size} Tf']
        y = page_height - margin_top
        for line in page_lines:
            safe_line = escape_pdf_text(line)
            content_cmds.append(f'1 0 0 1 {margin_left} {y} Tm ({safe_line}) Tj')
            y -= leading
        content_cmds.append('ET')
        content_stream = '\n'.join(content_cmds)
        content_obj_num = len(objects) + 1
        content_object_numbers.append(content_obj_num)
        objects.append(f'<< /Length {len(content_stream.encode("utf-8"))} >>\nstream\n{content_stream}\nendstream')

        page_obj_num = len(objects) + 1
        page_object_numbers.append(page_obj_num)
        objects.append(
            f'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {page_width} {page_height}] '
            f'/Resources << /Font << /F1 3 0 R >> >> /Contents {content_obj_num} 0 R >>'
        )

    kids = ' '.join(f'{n} 0 R' for n in page_object_numbers)
    objects[1] = f'<< /Type /Pages /Count {len(page_object_numbers)} /Kids [ {kids} ] >>'

    pdf = bytearray()
    pdf.extend(b'%PDF-1.4\n%\xe2\xe3\xcf\xd3\n')
    offsets = [0]

    for idx, obj in enumerate(objects, start=1):
        offsets.append(len(pdf))
        pdf.extend(f'{idx} 0 obj\n{obj}\nendobj\n'.encode('utf-8'))

    xref_start = len(pdf)
    pdf.extend(f'xref\n0 {len(objects) + 1}\n'.encode('utf-8'))
    pdf.extend(b'0000000000 65535 f \n')
    for off in offsets[1:]:
        pdf.extend(f'{off:010d} 00000 n \n'.encode('utf-8'))

    pdf.extend(
        (
            f'trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n'
            f'startxref\n{xref_start}\n%%EOF\n'
        ).encode('utf-8')
    )

    output_path.write_bytes(pdf)


def main():
    for csv_name, pdf_name, title in MAPPINGS:
        csv_path = DATA_DIR / csv_name
        pdf_path = DATA_DIR / pdf_name
        lines = build_lines(csv_path, title)
        write_simple_text_pdf(pdf_path, lines)
        print(f'Generated {pdf_path}')


if __name__ == '__main__':
    main()
