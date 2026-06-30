import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
from datetime import datetime, timedelta

# --- 1. CONTROL DE ACCESO PARA CELULARES ---
def verificar_password():
    if "autenticado" not in st.session_state:
        st.session_state["autenticado"] = False

    if st.session_state["autenticado"]:
        return True

    st.markdown("### 🔒 Acceso Técnico TAC")
    password_ingresada = st.text_input("Contraseña de la Mesa de Control:", type="password")
    
    if st.button("Ingresar al Buscador", use_container_width=True):
        if password_ingresada == "Tac2026*": # Cambia esta contraseña si lo deseas
            st.session_state["autenticado"] = True
            st.rerun()
        else:
            st.error("❌ Contraseña incorrecta. Inténtalo de nuevo.")
    return False

# --- 2. CONEXIÓN OPTIMIZADA A GOOGLE SHEETS ---
@st.cache_data(ttl=15) # Guardar en caché 15 segundos para evitar saturar la API
def cargar_datos_sheets():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    
    # Intenta leer desde los Secretos de Streamlit Cloud (Producción)
    if "gcp_service_account" in st.secrets:
        creds_dict = dict(st.secrets["gcp_service_account"])
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    else:
        # Respaldo local por si lo pruebas en tu computadora primero
        creds = ServiceAccountCredentials.from_json_keyfile_name("credenciales.json", scope)
        
    client = gspread.authorize(creds)
    
    # ID de tu Google Sheet oficial
    sheet_id = "10qZbXp4ayXjtITenLXaj7_E2y176O7JB28k28EcmbbM"
    documento = client.open_by_key(sheet_id)
    hoja = documento.get_sheet_by_id(0) 
    
    data = hoja.get_all_records()
    return pd.DataFrame(data)

# --- 3. INTERFAZ GRÁFICA RESPONSIVA (MÓVIL) ---
st.set_page_config(page_title="Validador TAC", page_icon="🛡️", layout="centered")

if verificar_password():
    st.markdown("## 🛡️ Buscador Móvil TAC")
    st.caption("Validación inmediata de garantías y recursos en campo.")

    try:
        df_base = cargar_datos_sheets()
        
        # Input de búsqueda ancho y cómodo para pantallas táctiles
        busqueda = st.text_input("📱 Ingresa Teléfono o Folio PISA:", placeholder="Ej. 2888822252")
        
        if busqueda:
            busqueda_clean = str(busqueda).strip()
            
            # Filtrado en la base de datos
            resultado = df_base[
                df_base['Telefono de'].astype(str).str.contains(busqueda_clean) | 
                df_base['Folio PISA'].astype(str).str.contains(busqueda_clean)
            ]
            
            if not resultado.empty:
                st.caption(f"📍 Registros encontrados: {len(resultado)}")
                
                # Contexto de tiempo sincronizado
                hoy = datetime.now()
                
                for index, fila in resultado.iterrows():
                    recurso = fila.get('Recurso', 'SIN RECURSO ASIGNADO')
                    telefono = fila.get('Telefono de', 'SIN NÚMERO')
                    fecha_str = str(fila.get('Fecha', '')).strip()
                    folio = fila.get('Folio PISA', 'N/A')
                    
                    es_garantia = False
                    fecha_formateada = fecha_str
                    dias_restantes = 0
                    
                    if fecha_str:
                        try:
                            fecha_dt = datetime.strptime(fecha_str, "%d/%m/%Y")
                            fecha_formateada = fecha_dt.strftime("%d/%m/%Y")
                            fecha_limite_garantia = fecha_dt + timedelta(days=60)
                            
                            if fecha_dt <= hoy <= fecha_limite_garantia:
                                es_garantia = True
                                dias_restantes = (fecha_limite_garantia - hoy).days
                        except ValueError:
                            pass

                    # Tarjeta visual compacta para el celular
                    with st.status(f"📞 Tel: {telefono} | Folio: {folio}", expanded=True, state="complete"):
                        
                        # Mensaje de garantía prioritario en la parte superior
                        if es_garantia:
                            st.error(f"🚨 **SE ENCUENTRA EN GARANTÍA**\n\nQuedan **{dias_restantes} días** de cobertura.")
                        else:
                            st.info("🔹 Fuera del periodo de garantía (60 días vencidos).")
                        
                        # Datos clave en formato grande
                        col1, col2 = st.columns(2)
                        with col1:
                            st.metric(label="👤 Técnico", value=recurso.split()[0] if recurso else "N/A")
                        with col2:
                            st.metric(label="📅 Registro", value=fecha_formateada)
                            
                        st.caption(f"Asignación completa: {recurso}")
            else:
                st.error("❌ No se encontró ningún registro que coincida.")
                
    except Exception as e:
        st.error("🚨 Error al conectar con la base de datos.")
        st.caption("Comprueba la configuración de los Secrets en el servidor.")
