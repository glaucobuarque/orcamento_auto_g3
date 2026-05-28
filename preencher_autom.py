import streamlit as st
from docxtpl import DocxTemplate
import io
import os
import tempfile
from pathlib import Path
from docx2pdf import convert

st.set_page_config(page_title="Gerador de Propostas - G3 Energias", layout="wide")

st.title("Gerador de Orçamentos Fotovoltaicos Automatizado ☀️ - G3")

# --- BLOCO DE ENTRADAS (Atualização em tempo real) ---

st.subheader("1. Dados Básicos e Consumo")
col1, col2, col3 = st.columns(3)
with col1:
    nome_cliente = st.text_input("Nome do Cliente", value="Cliente")
    tipo_telhado = st.selectbox("Tipo de Telhado", ["Metálico", "Cerâmico", "Fibrocimento"])
with col2:
    consumo_medio = st.number_input("Consumo Médio do Cliente (kWh/mês)", value=300, step=50)
with col3:
    valor_kwh = st.number_input("Tarifa Autoconsumo (R$/kWh)", value=1.14)
    valor_kwh_desc = st.number_input("Tarifa Injetada (R$/kWh)", value=0.84)

st.subheader("2. Parâmetros de Dimensionamento & Engenharia")
col4, col5, col6 = st.columns(3)
with col4:
    qtd_paineis = st.number_input("Qtd. Módulos", value=int(consumo_medio / 75.0), step=1)
    
    # CAMPO DESABILITADO PARA EDIÇÃO
    area_estimada = qtd_paineis * 2.7
    area_sistema = st.number_input("Área Total Calculada (m²)", value=float(f"{area_estimada:.2f}"), disabled=True)

with col5:
    tipo_inversor = st.radio("Tipo de Inversor", ["Microinversor", "Inversor String (Parede)"])
    q_inversores = int(qtd_paineis / 4) if tipo_inversor == "Microinversor" else 1
    qtd_inversores = st.number_input("Qtd. Inversores", value=q_inversores, step=1)

with col6:
    # CAMPO DESABILITADO PARA EDIÇÃO
    ger_sistema = st.number_input("Geração Estimada do Sistema (kWh/mês)", value=int(qtd_paineis * 75), disabled=True)

# -------------------------------------------------------------------------
# MOTOR DE FORMAÇÃO DE PREÇO DO ORÇAMENTO (CUSTO HARDWARE X LUCRO)
# -------------------------------------------------------------------------
st.subheader("3. Formação de Preço")
col_pr1, col_pr2, col_pr3 = st.columns(3)

with col_pr1:
    lucro_base = st.number_input("Lucro Base (Multiplicador. Ex: 30 = 30% a mais)", value=30, step=1)

# Lógica dos 3 itens:
item_1 = qtd_paineis * 900
item_2 = (qtd_inversores * 1000) if tipo_inversor == "Microinversor" else (qtd_inversores * 2500)
item_3 = (qtd_paineis / 4.0) * 180  # Cálculo proporcional de fixação

custo_base_hardware = item_1 + item_2 + item_3
custo_total = custo_base_hardware * (100 + lucro_base)/100.0

with col_pr2:
    st.number_input("Custo de Hardware (Base)", value=float(f"{custo_base_hardware:.2f}"), disabled=True)
with col_pr3:
    st.number_input("Preço de Venda Final (R$)", value=float(f"{custo_total:.2f}"), disabled=True)


st.subheader("4. Configurações Financeiras Ocultas (Premissas)")
with st.expander("Clique para ajustar taxas de reajuste, impostos e juros se necessário"):
    col_p1, col_p2, col_p3 = st.columns(3)
    with col_p1:
        cons_instantaneo = st.number_input("Porcentagem de Consumo Instantâneo (%)", value=30.0)
        valor_fiob = st.number_input("Valor FIO-B (R$)", value=0.18)
    with col_p2:
        reajuste_anual = st.number_input("Reajuste Anual de Energia (% a.a.)", value=10.0)
        selic = st.number_input("Taxa SELIC de Referência (% a.m.)", value=0.85)
    with col_p3:
        taxa_cartao_12x = st.number_input("Taxa de acréscimo para 12x no Cartão (%)", value=14.0)


# -------------------------------------------------------------------------
# MOTOR DE CÁLCULO MATEMÁTICO FINANCEIRO (Retorno e Economia)
# -------------------------------------------------------------------------

fator_auto = cons_instantaneo / 100.0
fator_inj = 1.0 - fator_auto

economia_mensal = (ger_sistema * fator_auto * valor_kwh) + (ger_sistema * fator_inj * valor_kwh_desc)
economia_total_1ano = economia_mensal * 12

custo_total_12x = custo_total * (1 + (taxa_cartao_12x / 100.0))
parcela_12x = custo_total_12x / 12

rentab_1ano = (economia_mensal / custo_total) * 100 if custo_total > 0 else 0

payback_total_meses = custo_total / economia_mensal if economia_mensal > 0 else 0
p_anos = int(payback_total_meses // 12)
p_meses = int(round(payback_total_meses % 12))

if p_anos > 0:
    payback_texto = f"{p_anos} ano{'s' if p_anos > 1 else ''} e {p_meses} me{'s' if p_meses == 1 else 'ses'}"
else:
    payback_texto = f"{p_meses} me{'s' if p_meses == 1 else 'ses'}"

economia_25anos = 0
ganho_ano_atual = economia_total_1ano
for ano in range(1, 26):
    economia_25anos += ganho_ano_atual
    ganho_ano_atual = ganho_ano_atual * (1 + (reajuste_anual / 100.0)) * (1 - 0.005)


# --- EXIBIÇÃO DE CARD COM MÉTRICAS EM TEMPO REAL ---
st.write("---")
st.subheader("📊 Resultados Calculados em Tempo Real")
m1, m2, m3, m4 = st.columns(4)

def fmt_moeda_tela(valor):
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

m1.metric("Custo Total de Venda", fmt_moeda_tela(custo_total))
m2.metric("Economia Mensal Estimada", fmt_moeda_tela(economia_mensal))
m3.metric("Valor da Parcela (12x CC)", fmt_moeda_tela(parcela_12x))
m4.metric("Tempo de Retorno (Payback)", payback_texto)
st.write("---")


# --- BOTÃO DE GERAÇÃO DE ARQUIVO DOCX E PDF ---
if st.button("🚀 Confirmar e Gerar Documentos (.docx e .pdf)"):
    with st.spinner("Gerando documentos, por favor aguarde..."):
        try:
            caminho_template = Path(__file__).parent / "template_proposta.docx"
            doc = DocxTemplate(caminho_template)
            
            if tipo_inversor == "Microinversor":
                desc_inversor = "MICRO INVERSOR MONOFÁSICO HOMOLOGADO - COM ACESSÓRIOS"
            else:
                desc_inversor = "INVERSOR STRING CENTRAL HOMOLOGADO - COM ACESSÓRIOS"

            def fmt_moeda(valor):
                return f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

            contexto = {
                "nome_cliente": nome_cliente,
                "ger_sistema": f"{ger_sistema:.0f}",
                "PP_SISTEMA": f"{((qtd_paineis * 620)/1000):.2f}".replace(".", ","), 
                "producao_mensal": f"{ger_sistema:.0f}",
                "CONS_MEDIO": f"{consumo_medio:.0f}",
                "AREA_SISTEMA": f"{area_sistema:.2f}".replace(".", ","),
                
                "qtd_paineis": int(qtd_paineis),
                "desc_inversor": desc_inversor,
                "qtd_micros": int(qtd_inversores),
                "qtd_string_cc": 1 if tipo_inversor == "Inversor String (Parede)" else 0,
                "qtd_string_ca": 1,
                "qtd_cabo_vermelho": 4,
                "qtd_cabo_preto": 4,
                "qtd_mc4": int(qtd_paineis),
                "tipo_telhado": tipo_telhado,
                "qtd_kit4mod": int(round(qtd_paineis / 4)),
                
                "VALOR_KWH": f"{valor_kwh:.2f}".replace(".", ","),
                "VALOR_kwh_descontado": f"{valor_kwh_desc:.2f}".replace(".", ","),
                "valor_fiob": f"{valor_fiob:.2f}".replace(".", ","),
                "reajuste_anual_perc": f"{reajuste_anual:.1f}".replace(".", ","),
                "Cons_instantaneo": f"{cons_instantaneo:.1f}".replace(".", ","),
                
                "Economia_media_mensaL_1ano": fmt_moeda(economia_mensal),
                "economia_total_1ano": fmt_moeda(economia_total_1ano),
                "Rentab_1ano": f"{rentab_1ano:.2f}".replace(".", ","),
                "RENTAB_1ANO": f"{rentab_1ano:.2f}% a.m.",
                "Economia_total_25anos": fmt_moeda(economia_25anos),
                
                "payback": payback_texto,
                "Payback": payback_texto,
                "SELIC": f"{selic:.2f}".replace(".", ","),
                
                "CUSTO_TOTAL": fmt_moeda(custo_total),
                "CUSTO_TOTAL_12X": fmt_moeda(parcela_12x)
            }
            
            doc.render(contexto)
            
            # --- SALVANDO NA MEMÓRIA PARA O DOCX ---
            buffer_docx = io.BytesIO()
            doc.save(buffer_docx)
            buffer_docx.seek(0)
            
            # --- CONVERSÃO PARA PDF ---
            # Cria um diretório temporário para salvar o arquivo físico e fazer a conversão
            pdf_criado_com_sucesso = False
            try:
                with tempfile.TemporaryDirectory() as tmpdir:
                    caminho_docx_temp = os.path.join(tmpdir, "temp.docx")
                    caminho_pdf_temp = os.path.join(tmpdir, "temp.pdf")
                    
                    # Salva o arquivo temporário no disco
                    doc.save(caminho_docx_temp)
                    
                    # Converte para PDF (Requer MS Word instalado na máquina)
                    convert(caminho_docx_temp, caminho_pdf_temp)
                    
                    # Lê o PDF gerado de volta para a memória
                    with open(caminho_pdf_temp, "rb") as pdf_file:
                        buffer_pdf = io.BytesIO(pdf_file.read())
                    
                    pdf_criado_com_sucesso = True
            except Exception as e_pdf:
                st.warning(f"O documento DOCX foi gerado, mas ocorreu um erro ao gerar o PDF. Verifique se o Microsoft Word está instalado e fechado. Detalhe: {e_pdf}")

            st.success("✅ Documentos processados com sucesso! Escolha o formato abaixo para baixar.")
            
            # Exibe os botões lado a lado
            col_btn1, col_btn2 = st.columns(2)
            
            with col_btn1:
                st.download_button(
                    label="📄 Baixar Proposta (.docx)",
                    data=buffer_docx,
                    file_name=f"Proposta_G3_Automatizada_{nome_cliente.replace(' ', '_')}.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                )
            


        except Exception as e:
            st.error(f"Erro ao processar arquivo de template: {e}")