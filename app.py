import streamlit as st
from sqlalchemy import create_engine, Column, Integer, String, Float, ForeignKey, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
import datetime
import io
import base64
from fpdf import FPDF
import random
import pandas as pd

# Veritabanı ayarları
Base = declarative_base()
engine = create_engine('sqlite:///fithole_clone.db')
Session = sessionmaker(bind=engine)
session = Session()

# Tablolar
class Project(Base):
    __tablename__ = 'projects'
    id = Column(Integer, primary_key=True)
    name = Column(String)
    customer = Column(String)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    cabinets = relationship("Cabinet", back_populates="project")

class Cabinet(Base):
    __tablename__ = 'cabinets'
    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey('projects.id'))
    cabinet_type = Column(String)
    width = Column(Float)
    height = Column(Float)
    depth = Column(Float)
    material = Column(String)
    project = relationship("Project", back_populates="cabinets")
    parts = relationship("Part", back_populates="cabinet")

class Part(Base):
    __tablename__ = 'parts'
    id = Column(Integer, primary_key=True)
    cabinet_id = Column(Integer, ForeignKey('cabinets.id'))
    name = Column(String)
    width = Column(Float)
    height = Column(Float)
    quantity = Column(Integer)
    cabinet = relationship("Cabinet", back_populates="parts")

# Veritabanı oluştur
Base.metadata.create_all(engine)

# Streamlit arayüz
st.set_page_config(layout="wide")
st.title("Fithole Klonu - Üretim Yönetimi")

# Yan Menü
menu = st.sidebar.radio("Menü", ["Proje Oluştur", "Kabin Ekle", "Kabin Listesi", "G-code & Çıktılar"])

if menu == "Proje Oluştur":
    with st.form("project_form"):
        st.subheader("Yeni Proje Oluştur")
        name = st.text_input("Proje Adı")
        customer = st.text_input("Müşteri Adı")
        submitted = st.form_submit_button("Projeyi Kaydet")

        if submitted and name and customer:
            new_project = Project(name=name, customer=customer)
            session.add(new_project)
            session.commit()
            st.success(f"Proje oluşturuldu: {name}")

if menu == "Kabin Ekle":
    st.subheader("Projelere Kabin Ekle")
    projects = session.query(Project).all()
    project_options = {f"{p.name} - {p.customer}": p.id for p in projects}

    if projects:
        selected_project_label = st.selectbox("Proje Seç", list(project_options.keys()))
        selected_project_id = project_options[selected_project_label]

        with st.form("cabinet_form"):
            cabinet_type = st.selectbox("Kabin Türü", ["Mutfak", "Portmanto", "Banyo", "TV Ünitesi"])
            width = st.number_input("Genişlik (mm)", min_value=100.0)
            height = st.number_input("Yükseklik (mm)", min_value=100.0)
            depth = st.number_input("Derinlik (mm)", min_value=100.0)
            material = st.selectbox("Malzeme", ["Sunta", "MDF", "Lake", "Laminat"])
            submit_cabinet = st.form_submit_button("Kabin Ekle")

            if submit_cabinet:
                new_cabinet = Cabinet(
                    project_id=selected_project_id,
                    cabinet_type=cabinet_type,
                    width=width,
                    height=height,
                    depth=depth,
                    material=material
                )
                session.add(new_cabinet)
                session.commit()

                # Parçaları otomatik oluştur (örnek algoritma)
                parts = [
                    ("Yan Panel", depth, height, 2),
                    ("Üst Panel", width, depth, 1),
                    ("Alt Panel", width, depth, 1),
                    ("Arka Panel", width, height, 1),
                    ("Kapak", width / 2, height, 2)
                ]
                for name, w, h, qty in parts:
                    part = Part(cabinet_id=new_cabinet.id, name=name, width=w, height=h, quantity=qty)
                    session.add(part)
                session.commit()
                st.success("Kabin ve parçalar başarıyla eklendi.")
    else:
        st.info("Lütfen önce bir proje oluşturun.")

if menu == "Kabin Listesi":
    st.subheader("Projeye Ait Kabin ve Parçalar")
    projects = session.query(Project).all()
    project_options = {f"{p.name} - {p.customer}": p.id for p in projects}

    if projects:
        selected_project_label = st.selectbox("Proje Seç (Listeleme)", list(project_options.keys()))
        selected_project_id = project_options[selected_project_label]
        cabinets = session.query(Cabinet).filter_by(project_id=selected_project_id).all()
        for cab in cabinets:
            st.markdown(f"### Kabin: {cab.cabinet_type} ({cab.width}x{cab.height}x{cab.depth} mm)")
            st.markdown(f"**Malzeme:** {cab.material}")
            parts = session.query(Part).filter_by(cabinet_id=cab.id).all()
            for part in parts:
                st.write(f"- {part.name}: {part.width} x {part.height} mm (Adet: {part.quantity})")
    else:
        st.info("Lütfen önce bir proje oluşturun.")

if menu == "G-code & Çıktılar":
    st.subheader("G-code Üretimi ve Çıktılar")
    cabinets = session.query(Cabinet).all()
    if cabinets:
        selected_cabinet = st.selectbox("Kabin Seç (G-code)", [f"{c.id} - {c.cabinet_type}" for c in cabinets])
        selected_cabinet_id = int(selected_cabinet.split(" - ")[0])
        selected_parts = session.query(Part).filter_by(cabinet_id=selected_cabinet_id).all()

        gcode_output = io.StringIO()
        for part in selected_parts:
            for i in range(part.quantity):
                gcode_output.write(f"; {part.name} ({i+1})\n")
                gcode_output.write(f"G0 X0 Y0\n")
                gcode_output.write(f"G1 X{part.width} Y0\n")
                gcode_output.write(f"G1 X{part.width} Y{part.height}\n")
                gcode_output.write(f"G1 X0 Y{part.height}\n")
                gcode_output.write(f"G1 X0 Y0\n\n")

        gcode_str = gcode_output.getvalue()
        st.text_area("G-code Çıktısı", gcode_str, height=300)

        b64 = base64.b64encode(gcode_str.encode()).decode()
        href = f'<a href="data:file/txt;base64,{b64}" download="gcode_output.nc">G-code İndir (.nc)</a>'
        st.markdown(href, unsafe_allow_html=True)

        st.subheader("Etiket PDF Oluştur")
        if st.button("Etiket PDF İndir"):
            pdf = FPDF()
            pdf.set_auto_page_break(auto=True, margin=15)
            pdf.add_page()
            pdf.set_font("Arial", size=12)

            for part in selected_parts:
                for i in range(part.quantity):
                    code = random.randint(100000, 999999)
                    pdf.cell(200, 10, txt=f"Etiket: {part.name} ({i+1}) - {part.width}x{part.height}mm - Kod: {code}", ln=True)

            pdf_output = io.BytesIO()
            pdf.output(pdf_output)
            pdf_output.seek(0)
            b64_pdf = base64.b64encode(pdf_output.read()).decode()
            href_pdf = f'<a href="data:application/pdf;base64,{b64_pdf}" download="etiketler.pdf">Etiket PDF İndir</a>'
            st.markdown(href_pdf, unsafe_allow_html=True)

        st.subheader("Parça Listesi Excel")
        if st.button("Excel Çıktısı İndir"):
            data = []
            for part in selected_parts:
                data.append({
                    "Parça Adı": part.name,
                    "Genişlik (mm)": part.width,
                    "Yükseklik (mm)": part.height,
                    "Adet": part.quantity
                })
            df = pd.DataFrame(data)
            excel_output = io.BytesIO()
            with pd.ExcelWriter(excel_output, engine='xlsxwriter') as writer:
                df.to_excel(writer, sheet_name='Parçalar', index=False)
            excel_output.seek(0)
            b64_excel = base64.b64encode(excel_output.read()).decode()
            href_excel = f'<a href="data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{b64_excel}" download="parca_listesi.xlsx">Excel İndir</a>'
            st.markdown(href_excel, unsafe_allow_html=True)
    else:
        st.info("Henüz eklenmiş bir kabin yok.")
