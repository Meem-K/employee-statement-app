import streamlit as st
import pandas as pd
import io
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import legal, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import os

# Page configuration
st.set_page_config(
    page_title="Employee Statement Generator",
    page_icon="📄",
    layout="centered"
)

# Title
st.title("📄 Employee Statement Generator")
st.markdown("Enter the EMIS code to generate the official employee statement")

# Load data
@st.cache_data
def load_data():
    try:
        df = pd.read_csv('employees.csv')
        return df
    except FileNotFoundError:
        st.error("employees.csv file not found. Please upload it below.")
        return None
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return None

# File uploader for first-time setup
df = load_data()
if df is None:
    uploaded_file = st.file_uploader("Upload employees.csv", type=['csv'])
    if uploaded_file is not None:
        df = pd.read_csv(uploaded_file)
        st.success("Data loaded successfully!")
        st.rerun()
    st.stop()

# Clean column names (remove spaces, special chars)
df.columns = df.columns.str.strip()

# Column mapping (based on your Excel structure)
COLUMN_MAP = {
    'emis': 'EMIS Code',
    'name': 'Name',
    'father': 'Father/Husband Name',
    'working_designation': 'Working Designation',
    'bps': 'BPS',
    'dob': 'Date of Birth',
    'first_entry': 'Date of 1st Entry',
    'current_posting': 'Current Posting Date',
    'cnic': 'CNIC #',
    'personnel': 'Personnel #',
    'mobile': 'Mobile #',
    'district': 'District',
    'tehsil': 'Tehsil',
    'school_name': 'Office/School'
}

# Find actual column names in the dataframe
def find_column(df, possible_names):
    for name in possible_names:
        for col in df.columns:
            if name.lower() in col.lower():
                return col
    return None

# Map actual columns
EMIS_COL = find_column(df, ['emis code', 'emis'])
NAME_COL = find_column(df, ['name'])
FATHER_COL = find_column(df, ['father', 'father/husband'])
DESIG_COL = find_column(df, ['working designation', 'designation'])
BPS_COL = find_column(df, ['bps'])
DOB_COL = find_column(df, ['date of birth', 'dob'])
FIRST_ENTRY_COL = find_column(df, ['date of 1st entry', '1st entry'])
POSTING_COL = find_column(df, ['current posting date', 'posting date'])
CNIC_COL = find_column(df, ['cnic #', 'cnic'])
PERSONNEL_COL = find_column(df, ['personnel #', 'personnel'])
MOBILE_COL = find_column(df, ['mobile #', 'mobile'])
DISTRICT_COL = find_column(df, ['district'])
TEHSIL_COL = find_column(df, ['tehsil'])
SCHOOL_COL = find_column(df, ['office/school', 'school'])

def extract_bps(value):
    """Extract numeric BPS from string like 'BPS-12' or '12'"""
    if pd.isna(value):
        return 0
    value_str = str(value)
    numbers = ''.join([c for c in value_str if c.isdigit()])
    return int(numbers) if numbers else 0

def is_class_iv(designation, bps):
    """Determine if employee is Class IV"""
    if bps <= 6:
        return True
    desig_upper = str(designation).upper()
    keywords = ['CLASS IV', 'CLASS-IV', 'QASID', 'CHOWKIDAR', 'MALI', 'SWEEPER']
    return any(keyword in desig_upper for keyword in keywords)

def format_date(date_val):
    """Format date to dd/mm/yyyy"""
    if pd.isna(date_val):
        return ""
    try:
        if isinstance(date_val, str):
            # Try different formats
            for fmt in ['%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y', '%Y/%m/%d']:
                try:
                    d = datetime.strptime(date_val.split()[0], fmt)
                    return d.strftime('%d/%m/%Y')
                except:
                    continue
        else:
            return date_val.strftime('%d/%m/%Y')
    except:
        return str(date_val)
    return ""

def create_pdf(employees_data, school_name, district, tehsil, emis_code):
    """Create PDF using reportlab"""
    buffer = io.BytesIO()
    
    # Create PDF document - Legal size, Landscape
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(legal),
        leftMargin=0.2*inch,
        rightMargin=0.2*inch,
        topMargin=0.2*inch,
        bottomMargin=0.2*inch
    )
    
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'TitleStyle',
        parent=styles['Normal'],
        fontSize=10,
        alignment=0,  # Left align
        spaceAfter=6
    )
    
    header_style = ParagraphStyle(
        'HeaderStyle',
        parent=styles['Normal'],
        fontSize=9,
        alignment=0,
        fontName='Helvetica-Bold'
    )
    
    cell_style = ParagraphStyle(
        'CellStyle',
        parent=styles['Normal'],
        fontSize=8,
        alignment=0
    )
    
    # Build content
    story = []
    
    # Row 1: Monthly Statement header
    month_year = datetime.now().strftime('%B %Y')
    row1_text = f"Monthly Statement For The Month of: {month_year}  School Name: {school_name}  EMIS Code: {emis_code}"
    story.append(Paragraph(row1_text, title_style))
    story.append(Spacer(1, 6))
    
    # Row 2: Location details
    row2_text = f"District: {district}    Tehsil: {tehsil}    Circle:     UC:     VC:"
    story.append(Paragraph(row2_text, title_style))
    story.append(Spacer(1, 6))
    
    # Row 3: STAFF STATEMENT
    story.append(Paragraph("STAFF STATEMENT", header_style))
    story.append(Spacer(1, 6))
    
    # Separate Teaching and Class IV
    teaching = [e for e in employees_data if not e['is_class_iv']]
    class_iv = [e for e in employees_data if e['is_class_iv']]
    
    # Sort by BPS descending
    teaching.sort(key=lambda x: x['bps'], reverse=True)
    class_iv.sort(key=lambda x: x['bps'], reverse=True)
    
    # Table headers
    headers = [
        'Sr.', 'EMPLOYEE NAME', "FATHER'S NAME", 'DESIGNATION (BPS)',
        'D.O.B.', 'Date of 1st Appointment', 'Present School Charge Date',
        'Present Post Charge Date', 'Qualification\n(Acad. & Prof.)',
        'CNIC No.', 'Personal No.', 'Contact No.'
    ]
    
    # Build teaching table data
    teaching_data = [headers]
    for idx, emp in enumerate(teaching, 1):
        teaching_data.append([
            str(idx),
            Paragraph(emp['name'], cell_style),
            Paragraph(emp['father'], cell_style),
            f"{emp['designation']} (BPS-{emp['bps']})",
            emp['dob'],
            emp['first_entry'],
            emp['school_entry'],
            emp['post_entry'],
            "Acad:\nProf:",
            emp['cnic'],
            emp['personnel'],
            emp['contact']
        ])
    
    # Add empty rows after teaching (2 rows with hidden text in qualification column)
    for _ in range(2):
        teaching_data.append([
            '', '', '', '', '', '', '', '',
            'Qualification Qualification',  # This text will be hidden (white on white)
            '', '', ''
        ])
    
    # Create teaching table
    if len(teaching_data) > 1:
        teaching_table = Table(teaching_data, repeatRows=1)
        teaching_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 7),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ]))
        
        # Hide the "Qualification Qualification" text (make it white on white)
        # Note: In reportlab, we set text color to white to hide it
        for row_idx in range(len(teaching_data) - 2, len(teaching_data)):
            teaching_table.setStyle(TableStyle([
                ('TEXTCOLOR', (8, row_idx), (8, row_idx), colors.white),
            ]))
        
        story.append(teaching_table)
        story.append(Spacer(1, 12))
    
    # Class IV Section
    if class_iv:
        # Class IV header
        story.append(Paragraph("Class IV Detail:", header_style))
        story.append(Spacer(1, 6))
        
        # Build Class IV table data
        class_iv_data = [headers]
        for idx, emp in enumerate(class_iv, 1):
            class_iv_data.append([
                str(idx),
                Paragraph(emp['name'], cell_style),
                Paragraph(emp['father'], cell_style),
                f"{emp['designation']} (BPS-{emp['bps']})",
                emp['dob'],
                emp['first_entry'],
                emp['school_entry'],
                emp['post_entry'],
                "Acad:\nProf:",
                emp['cnic'],
                emp['personnel'],
                emp['contact']
            ])
        
        # Add empty row after Class IV (1 row with hidden text)
        class_iv_data.append([
            '', '', '', '', '', '', '', '',
            'Qualification Qualification',
            '', '', ''
        ])
        
        class_iv_table = Table(class_iv_data, repeatRows=1)
        class_iv_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 7),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ]))
        
        # Hide the "Qualification Qualification" text
        last_row = len(class_iv_data) - 1
        class_iv_table.setStyle(TableStyle([
            ('TEXTCOLOR', (8, last_row), (8, last_row), colors.white),
        ]))
        
        story.append(class_iv_table)
        story.append(Spacer(1, 12))
    
    # Add blank rows before submission date (2 rows, no borders)
    for _ in range(2):
        story.append(Spacer(1, 12))
    
    # Submission Date row
    submission_text = f"Submission Date: {datetime.now().strftime('%d/%m/%Y')}                                                             Sign & Seal of Principal/Head Master"
    story.append(Paragraph(submission_text, header_style))
    
    # Build PDF
    doc.build(story)
    buffer.seek(0)
    return buffer

# Input form
with st.form("emis_form"):
    emis_code = st.text_input("EMIS Code", placeholder="Enter EMIS code (e.g., 20116 or S0129)")
    submitted = st.form_submit_button("📄 Generate Statement", use_container_width=True)

if submitted:
    if not emis_code:
        st.error("Please enter an EMIS code")
    else:
        # Find matching employees
        matching_employees = df[df[EMIS_COL].astype(str).str.strip() == emis_code.strip()]
        
        if len(matching_employees) == 0:
            st.error(f"No employees found for EMIS code: {emis_code}")
        else:
            with st.spinner("Generating statement..."):
                # Get school details
                school_name = matching_employees.iloc[0][SCHOOL_COL] if SCHOOL_COL else "Unknown School"
                district = matching_employees.iloc[0][DISTRICT_COL] if DISTRICT_COL else ""
                tehsil = matching_employees.iloc[0][TEHSIL_COL] if TEHSIL_COL else ""
                
                # Build employee data list
                employees = []
                for _, row in matching_employees.iterrows():
                    bps = extract_bps(row[BPS_COL]) if BPS_COL else 0
                    designation = row[DESIG_COL] if DESIG_COL else ""
                    
                    emp = {
                        'name': str(row[NAME_COL]) if NAME_COL and not pd.isna(row[NAME_COL]) else "",
                        'father': str(row[FATHER_COL]) if FATHER_COL and not pd.isna(row[FATHER_COL]) else "",
                        'designation': str(designation),
                        'bps': bps,
                        'dob': format_date(row[DOB_COL] if DOB_COL else None),
                        'first_entry': format_date(row[FIRST_ENTRY_COL] if FIRST_ENTRY_COL else None),
                        'school_entry': format_date(row[POSTING_COL] if POSTING_COL else None),
                        'post_entry': format_date(row[POSTING_COL] if POSTING_COL else None),
                        'cnic': str(row[CNIC_COL]) if CNIC_COL and not pd.isna(row[CNIC_COL]) else "",
                        'personnel': str(row[PERSONNEL_COL]) if PERSONNEL_COL and not pd.isna(row[PERSONNEL_COL]) else "",
                        'contact': str(row[MOBILE_COL]) if MOBILE_COL and not pd.isna(row[MOBILE_COL]) else "",
                        'is_class_iv': is_class_iv(designation, bps)
                    }
                    employees.append(emp)
                
                # Generate PDF
                pdf_buffer = create_pdf(employees, school_name, district, tehsil, emis_code)
                
                # Provide download button
                st.success(f"✅ Found {len(employees)} employee(s)")
                st.download_button(
                    label="📥 Download Statement (PDF)",
                    data=pdf_buffer,
                    file_name=f"Official_Statement_EMIS_{emis_code}.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )

# Footer
st.markdown("---")
st.caption("Official Employee Statement Generator | Data source: Posted Employees List")