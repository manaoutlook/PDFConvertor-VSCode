import logging
import tempfile
import pandas as pd
import tabula
import os
from datetime import datetime
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter

def clean_amount(amount_str):
    """Clean and format amount strings"""
    if pd.isna(amount_str):
        return ''
    # Remove currency symbols and cleanup
    amount_str = str(amount_str).replace('$', '').replace(',', '').strip()
    # Handle brackets for negative numbers
    if '(' in amount_str and ')' in amount_str:
        amount_str = '-' + amount_str.replace('(', '').replace(')', '')
    return amount_str

def convert_pdf(pdf_path: str, output_format: str = 'excel'):
    """Convert PDF bank statement to Excel/CSV using tabula-py"""
    try:
        logging.info(f"Starting conversion of {pdf_path}")

        # Extract tables from all pages with specific settings for ANZ statements
        tables = tabula.read_pdf(
            pdf_path,
            pages='all',
            multiple_tables=True,
            guess=True,  # Changed to True for better table detection
            lattice=False,  # Changed to False as ANZ statements don't use grid lines
            stream=True,
            pandas_options={'header': None}
        )

        logging.info(f"Found {len(tables)} tables in the PDF")

        if not tables:
            logging.error("No tables found in the PDF")
            return None

        # Process and combine tables
        processed_data = []
        for idx, table in enumerate(tables):
            logging.debug(f"Processing table {idx+1}, shape: {table.shape}")
            if len(table.columns) >= 4:  # Ensure table has enough columns
                # Clean column names
                table.columns = range(len(table.columns))

                # Skip header rows and process each row
                for _, row in table.iterrows():
                    # Skip rows that don't look like transactions
                    if pd.isna(row[0]) or not str(row[0]).strip():
                        continue

                    try:
                        # Try to parse the date to validate it's a transaction row
                        date_str = str(row[0]).strip()
                        datetime.strptime(date_str, '%d %b %y')

                        transaction = {
                            'Date': date_str,
                            'Description': str(row[1]).strip() if not pd.isna(row[1]) else '',
                            'Debit': clean_amount(row[2]),
                            'Credit': clean_amount(row[3]),
                            'Balance': clean_amount(row[4]) if len(row) > 4 else ''
                        }
                        processed_data.append(transaction)
                        logging.debug(f"Processed transaction: {transaction}")
                    except (ValueError, TypeError) as e:
                        logging.debug(f"Skipping row, not a valid transaction: {row[0]}, error: {str(e)}")
                        continue

        if not processed_data:
            logging.error("No valid transactions found after processing")
            return None

        logging.info(f"Successfully processed {len(processed_data)} transactions")

        # Convert to DataFrame
        df = pd.DataFrame(processed_data)

        # Create output file
        temp_file = tempfile.NamedTemporaryFile(delete=False)

        if output_format == 'excel':
            output_path = f"{temp_file.name}.xlsx"
            # Apply formatting
            with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name='Transactions')
                workbook = writer.book
                worksheet = writer.sheets['Transactions']

                # Format headers
                header_font = Font(bold=True)
                header_fill = PatternFill(start_color='D3D3D3', end_color='D3D3D3', fill_type='solid')
                header_alignment = Alignment(horizontal='center')

                for col in range(len(df.columns)):
                    cell = worksheet.cell(row=1, column=col+1)
                    cell.font = header_font
                    cell.fill = header_fill
                    cell.alignment = header_alignment

                # Auto-adjust column widths
                for idx, column in enumerate(worksheet.columns, 1):
                    max_length = 0
                    column = [cell for cell in column]
                    for cell in column:
                        try:
                            if len(str(cell.value)) > max_length:
                                max_length = len(str(cell.value))
                        except:
                            pass
                    adjusted_width = (max_length + 2)
                    worksheet.column_dimensions[get_column_letter(idx)].width = adjusted_width
        else:
            output_path = f"{temp_file.name}.csv"
            df.to_csv(output_path, index=False)

        logging.info(f"Successfully created output file: {output_path}")
        return output_path

    except Exception as e:
        logging.error(f"Error in conversion: {str(e)}")
        return None