import streamlit as st
from jinja2 import Template
from datetime import date
import io
from pathlib import Path

st.set_page_config(page_title="Gerador de Propostas - G3 Energias", layout="wide")

st.title("Gerador de Orçamentos Fotovoltaicos Automatizado ☀️ - G3")

# --- BLOCO DE ENTRADAS (Atualização em tempo real) ---

st.subheader("1. Dados Básicos e Consumo")
col1, col2, col3 = st.columns(3)
with col1:
    nome_cliente = st.text_input("Nome do Cliente", value="Cliente")
    numero_proposta = st.text_input("Número da Proposta", value=f"0{date.today().day}-{date.today().month}/{date.today().year}")
    tipo_telhado = st.selectbox("Tipo de Telhado", ["Metálico", "Cerâmico", "Fibrocimento"])
with col2:
    consumo_medio = st.number_input("Consumo Médio do Cliente (kWh/mês)", value=300, step=75)
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
    q_inversores = int(qtd_paineis // 4) if tipo_inversor == "Microinversor" else 1
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
custo_total = custo_base_hardware / lucro_base * 100.0

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


# --- BOTÃO DE GERAÇÃO DO HTML DA PROPOSTA ---
if st.button("🚀 Confirmar e Gerar Proposta (.html)"):
    with st.spinner("Gerando proposta, por favor aguarde..."):
        try:
            caminho_template = Path(__file__).parent / "Modelo_Solar_template.html"
            template_html = caminho_template.read_text(encoding="utf-8")
            template = Template(template_html)

            def fmt_moeda(valor):
                return f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

            def fmt_num(valor, casas=2):
                return f"{valor:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")

            # --- Descrição do inversor e montagem da lista de equipamentos ---
            if tipo_inversor == "Microinversor":
                desc_inversor = "Micro Inversor Monofásico Homologado — com acessórios"
            else:
                desc_inversor = "Inversor String Central Homologado — com acessórios"

            qtd_string_cc = 1 if tipo_inversor == "Inversor String (Parede)" else 0
            qtd_kit4mod = int(round(qtd_paineis / 4))

            itens_brutos = [
                ("Módulo Fotovoltaico 620W Bifacial Frame Composto N-Type", f"{int(qtd_paineis)} un"),
                (desc_inversor, f"{int(qtd_inversores)} un"),
            ]
            if qtd_string_cc:
                itens_brutos.append(("String Box CC c/ DPS", f"{int(qtd_string_cc)} un"))
            itens_brutos += [
                ("String Box CA c/ DJ DPS", "1 un"),
                ("Cabo Solar CC Vermelho 4,00 mm² — 25 m", "4 un"),
                ("Cabo Solar CC Preto 4,00 mm² — 25 m", "4 un"),
                ("Par Conector MC4 para Sistema Fotovoltaico (cabo 2,5/4/6 mm²)", f"{int(qtd_paineis)} un"),
                ("Placa de Geração Própria Metálica Padrão", "1 un"),
                ("Material de Infraestrutura (tubulação e fiação CA)", "—"),
                (f"Kit Inst. 04 Módulos 620W {tipo_telhado} — com 4 Perfil 2,4 m H38", f"{int(qtd_kit4mod)} un"),
            ]

            romanos = ["I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X", "XI", "XII"]
            equipamentos = [
                {"num": romanos[i], "desc": desc, "qty": qty}
                for i, (desc, qty) in enumerate(itens_brutos)
            ]

            contexto = {
                "nome_cliente": nome_cliente,
                "numero_proposta": numero_proposta,
                "data_proposta": date.today().strftime("%d/%m/%Y"),

                "potencia_kwp": fmt_num((qtd_paineis * 620) / 1000, 2),
                "producao_mensal": f"{ger_sistema:.0f}",
                "consumo_medio": f"{consumo_medio:.0f}",
                "area_sistema": fmt_num(area_sistema, 2),

                "economia_25anos": fmt_moeda(economia_25anos),
                "payback_texto": payback_texto,
                "economia_mensal": fmt_moeda(economia_mensal),
                "rentab_1ano": fmt_num(rentab_1ano, 2),

                "valor_kwh": fmt_num(valor_kwh, 2),
                "valor_kwh_desc": fmt_num(valor_kwh_desc, 2),
                "valor_fiob": fmt_num(valor_fiob, 2),
                "reajuste_anual": fmt_num(reajuste_anual, 1),
                "cons_instantaneo": fmt_num(cons_instantaneo, 1),
                "economia_total_1ano": fmt_moeda(economia_total_1ano),

                "custo_total": fmt_moeda(custo_total),
                "parcela_12x": fmt_moeda(parcela_12x),

                "equipamentos": equipamentos,
            }

            html_final = template.render(contexto)

            st.success("✅ Proposta gerada com sucesso! Baixe o HTML abaixo.")

            st.download_button(
                label="📄 Baixar Proposta (.html)",
                data=html_final.encode("utf-8"),
                file_name=f"Proposta_G3_{nome_cliente.replace(' ', '_')}.html",
                mime="text/html",
            )

            st.caption(
                "Abra o arquivo .html baixado em qualquer navegador e clique no botão "
                "**'Gerar PDF'** (canto inferior direito) para salvar a proposta como PDF."
            )

            with st.expander("👁️ Pré-visualizar proposta"):
                st.components.v1.html(html_final, height=800, scrolling=True)

        except Exception as e:
            st.error(f"Erro ao processar o template HTML: {e}")
