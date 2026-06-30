import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
from datetime import datetime, timedelta

# Conectar con la Google Sheet usando los Secrets de la Nube
@st.cache_data(ttl=15)
def cargar_datos_sheets():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    
    if "gcp_service_account" in st.secrets:
        creds_dict = dict(st.secrets["gcp_service_account"])
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    else:
        creds = ServiceAccountCredentials.from_json_keyfile_name("credenciales.json", scope)
        
    client = gspread.authorize(creds)
    
    sheet_id = "10qZbXp4ayXjtITenLXaj7_E2y176O7JB28k28EcmbbM"
    documento = client.open_by_key(sheet_id)
    hoja = documento.get_worksheet(0) 
    
    data = hoja.get_all_records()
    df = pd.DataFrame(data)
    
    # Limpieza automática de columnas (evita fallos por espacios en blanco ocultos)
    df.columns = df.columns.str.strip()
    
    return df

# Configuración Web optimizada para teléfonos celulares
st.set_page_config(page_title="Validador de Garantías TAC", page_icon="🛡️", layout="centered")
st.title("🛡️ Buscador y Validador de Garantías TAC")
st.caption("Consulta rápida de estatus de garantías y asignación de recursos en campo.")

try:
    df_base = cargar_datos_sheets()
    st.success("✅ Base de datos conectada en vivo.")
    st.markdown("---")
    
    # Entrada de búsqueda interactiva
    busqueda = st.text_input("Ingresa el número telefónico o Folio PISA a consultar:", placeholder="Ej. 2888822252")
    
    if busqueda:
        busqueda_clean = str(busqueda).strip()
        
        # CORRECCIÓN AQUÍ: Ahora busca bajo la columna 'TELEFONO' exacta
        resultado = df_base[
            df_base['TELEFONO'].astype(str).str.contains(busqueda_clean) | 
            df_base['Folio PISA'].astype(str).str.contains(busqueda_clean)
        ]
        
        if not resultado.empty:
            st.subheader(f"📋 Resultados encontrados ({len(resultado)}):")
            hoy = datetime.now()
            
            for index, fila in resultado.iterrows():
                # Extraer variables requeridas (se limpian los nombres por seguridad)
                recurso = fila.get('Recurso', 'SIN RECURSO ASIGNADO')
                telefono = fila.get('TELEFONO', 'SIN NÚMERO')
                fecha_str = str(fila.get('Fecha', '')).strip()
                folio = fila.get('Folio PISA', 'N/A')
                
                # Evaluación de la Garantía (60 días posteriores a la fecha del registro)
                es_garantia = False
                fecha_formateada = "Fecha no válida"
                dias_restantes = 0

                if fecha_str:
                    try:
                        fecha_dt = datetime.strptime(fecha_str, "%d/%m/%Y")
                        fecha_formateada = fecha_dt.strftime("%d de %B, %Y")
                        fecha_limite_garantia = fecha_dt + timedelta(days=60)
                        
                        if fecha_dt <= hoy <= fecha_limite_garantia:
                            es_garantia = True
                            dias_restantes = (fecha_limite_garantia - hoy).days
                    except ValueError:
                        fecha_formateada = f"{fecha_str} (Formato no reconocido)"

                # Tarjeta móvil adaptable estructurada por cada registro
                with st.status(f"📞 Teléfono: {telefono} | Folio: {folio}", expanded=True, state="complete"):
                    
                    if es_garantia:
                        st.error(f"🚨 **SE ENCUENTRA EN GARANTÍA**\n\nQuedan **{dias_restantes} días** de cobertura estándar.")
                    else:
                        st.info("🔹 Fuera del periodo de garantía estándar (60 días).")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric(label="👤 Técnico", value=recurso.split()[0] if recurso else "N/A")
                    with col2:
                        st.metric(label="📅 Registro", value=fecha_dt.strftime("%d/%m/%Y") if fecha_str else "N/A")
                        
                    st.caption(f"Asignación completa registrada: {recurso}")
        else:
            st.error("❌ No se encontró ningún registro que coincida con la búsqueda.")
            
except Exception as e:
    st.error("🚨 Error al procesar los datos de la consulta.")
    st.info("Verifica que las columnas 'TELEFONO', 'Folio PISA', 'Fecha' y 'Recurso' existan en la fila 1 de tu hoja.")
    st.exception(e)
    st.info("Asegúrate de que la cuenta de servicio de Google tenga permisos de lector en tu hoja.")
    st.exception(e)
