import streamlit as st
import pandas as pd
import io
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import legal, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
import os
import re

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
def load_data(uploaded_file=None):
    try:
        if uploaded_file is not None:
            # Read uploaded CSV
            df = pd.read_csv(uploaded_file)
            return df
        elif os.path.exists('employees.csv'):
            # Read local CSV
            df = pd.read_csv('employees.csv')
            return df
        else:
            return None
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return None

# File uploader for first-time setup or if file not found
df = None
uploaded_file = st.file_uploader("Upload Employee Data (CSV file)", type=['csv'], key="data_uploader")

if uploaded_file is not None:
    df = load_data(uploaded_file)
    if df is not None:
        st.success(f"✅ Loaded {len(df)} employee records!")
else:
    df = load_data()
    if df is None:
        st.info("📁 Please upload your employees.csv file to get started")
        st.stop()

# Clean column names (remove spaces, special chars)
df.columns = df.columns.str.strip()

# Helper functions
def find_column(df, possible_names):
    """Find column by possible names (case-insensitive)"""
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

if not EMIS_COL:
    st.error("Could not find EMIS column in the uploaded file")
    st.stop()

def extract_bps(value):
    """Extract numeric BPS from string like 'BPS-12' or '12'"""
    if pd.isna(value):
        return 0
    value_str = str(value)
    numbers = re.sub(r'[^0-9]', '', value_str)
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
                    # Handle "2025-09-09 00:00:00" format
                    clean_date = date_val.split()[0]
                    d = datetime.strptime(clean_date, fmt)
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
        alignment=0,
        spaceAfter=6,
        fontName='Helvetica'
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
        alignment=0,
        fontName='Helvetica'
    )
    
    # Build content
    story = []
    
    # Row 1: Monthly Statement header
    month_year = datetime.now().strftime('%B %Y')
    row1_text = f"Monthly Statement For The Month of: {month_year}  School Name: {school_name}  EMIS Code: {emis_code}"
    story.append(Paragraph(row1_text, title_style))
    story.append(Spacer(1, 3))
    
    # Row 2: Location details
    row2_text = f"District: {district}    Tehsil: {tehsil}    Circle:     UC:     VC:"
    story.append(Paragraph(row2_text, title_style))
    story.append(Spacer(1, 6))
    
    # Row 3: STAFF STATEMENT header
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
            Paragraph(emp['name'][:50] if len(emp['name']) > 50 else emp['name'], cell_style),
            Paragraph(emp['father'][:50] if len(emp['father']) > 50 else emp['father'], cell_style),
            f"{emp['designation'][:40]} (BPS-{emp['bps']})" if len(emp['designation']) > 40 else f"{emp['designation']} (BPS-{emp['bps']})",
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
            'Qualification Qualification',
            '', '', ''
        ])
    
    # Create teaching table
    if len(teaching_data) > 1:
        # Calculate column widths
        col_widths = [0.5*inch, 1.5*inch, 1.5*inch, 1.8*inch, 0.8*inch, 0.9*inch, 0.9*inch, 0.9*inch, 1.2*inch, 1.0*inch, 0.8*inch, 0.8*inch]
        
        teaching_table = Table(teaching_data, colWidths=col_widths, repeatRows=1)
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
                Paragraph(emp['name'][:50] if len(emp['name']) > 50 else emp['name'], cell_style),
                Paragraph(emp['father'][:50] if len(emp['father']) > 50 else emp['father'], cell_style),
                f"{emp['designation'][:40]} (BPS-{emp['bps']})" if len(emp['designation']) > 40 else f"{emp['designation']} (BPS-{emp['bps']})",
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
        
        col_widths = [0.5*inch, 1.5*inch, 1.5*inch, 1.8*inch, 0.8*inch, 0.9*inch, 0.9*inch, 0.9*inch, 1.2*inch, 1.0*inch, 0.8*inch, 0.8*inch]
        
        class_iv_table = Table(class_iv_data, colWidths=col_widths, repeatRows=1)
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
    
    # Add blank rows before submission date (2 rows, no borders - just spacers)
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
        emis_code_clean = emis_code.strip()
        matching_employees = df[df[EMIS_COL].astype(str).str.strip() == emis_code_clean]
        
        if len(matching_employees) == 0:
            st.error(f"No employees found for EMIS code: {emis_code}")
        else:
            with st.spinner("Generating statement..."):
                # Get school details
                school_name = matching_employees.iloc[0][SCHOOL_COL] if SCHOOL_COL else "Unknown School"
                district = matching_employees.iloc[0][DISTRICT_COL] if DISTRICT_COL else ""
                tehsil = matching_employees.iloc[0][TEHSIL_COL] if TEHSIL_COL else ""
                
                # Handle NaN values
                if pd.isna(school_name):
                    school_name = "Unknown School"
                if pd.isna(district):
                    district = ""
                if pd.isna(tehsil):
                    tehsil = ""
                
                # Build employee data list
                employees = []
                for _, row in matching_employees.iterrows():
                    bps = extract_bps(row[BPS_COL]) if BPS_COL else 0
                    designation = row[DESIG_COL] if DESIG_COL else ""
                    
                    # Handle NaN values
                    name_val = row[NAME_COL] if NAME_COL else ""
                    if pd.isna(name_val):
                        name_val = ""
                    
                    father_val = row[FATHER_COL] if FATHER_COL else ""
                    if pd.isna(father_val):
                        father_val = ""
                    
                    designation_val = designation if not pd.isna(designation) else ""
                    cnic_val = row[CNIC_COL] if CNIC_COL else ""
                    if pd.isna(cnic_val):
                        cnic_val = ""
                    
                    personnel_val = row[PERSONNEL_COL] if PERSONNEL_COL else ""
                    if pd.isna(personnel_val):
                        personnel_val = ""
                    
                    contact_val = row[MOBILE_COL] if MOBILE_COL else ""
                    if pd.isna(contact_val):
                        contact_val = ""
                    
                    emp = {
                        'name': str(name_val),
                        'father': str(father_val),
                        'designation': str(designation_val),
                        'bps': bps,
                        'dob': format_date(row[DOB_COL] if DOB_COL else None),
                        'first_entry': format_date(row[FIRST_ENTRY_COL] if FIRST_ENTRY_COL else None),
                        'school_entry': format_date(row[POSTING_COL] if POSTING_COL else None),
                        'post_entry': format_date(row[POSTING_COL] if POSTING_COL else None),
                        'cnic': str(cnic_val),
                        'personnel': str(personnel_val),
                        'contact': str(contact_val),
                        'is_class_iv': is_class_iv(designation_val, bps)
                    }
                    employees.append(emp)
                
                # Generate PDF
                try:
                    pdf_buffer = create_pdf(employees, str(school_name), str(district), str(tehsil), emis_code_clean)
                    
                    # Provide download button
                    st.success(f"✅ Found {len(employees)} employee(s)")
                    st.download_button(
                        label="📥 Download Statement (PDF)",
                        data=pdf_buffer,
                        file_name=f"Official_Statement_EMIS_{emis_code_clean}.pdf",
                        mime="application/pdf",
                        use_container_width=True
                    )
                except Exception as pdf_error:
                    st.error(f"Error generating PDF: {str(pdf_error)}")

# Footer
st.markdown("---")
st.caption("Official Employee Statement Generator | Data source: Posted Employees List")
