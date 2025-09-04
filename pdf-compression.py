import os
from pypdf import PdfReader, PdfWriter

def split_pdf_by_size(input_file, max_size_mb=4):
    reader = PdfReader(input_file)
    total_pages = len(reader.pages)
    max_size_bytes = int(max_size_mb * 1024 * 1024)

    part = 1
    writer = PdfWriter()

    for i, page in enumerate(reader.pages):
        writer.add_page(page)

        # Save temporarily to check size
        temp_file = f"part_{part}.pdf"
        with open(temp_file, "wb") as f:
            writer.write(f)

        # If size exceeds, roll back last page
        if os.path.getsize(temp_file) > max_size_bytes:
            # remove last added page
            writer.remove_page(-1)

            # finalize previous part
            with open(temp_file, "wb") as f:
                writer.write(f)

            print(f"Created {temp_file} ({os.path.getsize(temp_file)/1024/1024:.2f} MB)")

            # start a new writer with the rolled back page
            part += 1
            writer = PdfWriter()
            writer.add_page(page)

    # save last chunk
    if writer.pages:
        temp_file = f"part_{part}.pdf"
        with open(temp_file, "wb") as f:
            writer.write(f)
        print(f"Created {temp_file} ({os.path.getsize(temp_file)/1024/1024:.2f} MB)")

# Example usage
split_pdf_by_size("input.pdf", max_size_mb=4)
