import streamlit as st
import pandas as pd
import numpy as np
import os
import time
import altair as alt
import base64
from PIL import Image, UnidentifiedImageError

from dotenv import load_dotenv
load_dotenv()

# --- Módulos Internos ---
from src.data_loader import load_data
from api_client import chamar_api_bioms, obter_lista_exercicios, consultar_media_normativa, calcular_corrida_api
from src.statistics import BioMSStatistics
from src.interpretation import BioMSInterpreter

try:
    from src.pdf_generator import criar_pdf, criar_relatorio_grupo,criar_relatorio_zscore_universal, criar_relatorio_normativo_longitudinal
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False

# --- Configuração da Página ---
st.set_page_config(
    page_title="BioMS Analytics Pro",
    page_icon="🧬",
    layout="wide",
    initial_sidebar_state="expanded"
)



# --- CSS Premium ---
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .stMetric { 
        background-color: #ffffff; 
        padding: 20px; 
        border-radius: 12px; 
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        border-left: 5px solid #2980b9;
    }
    h1, h2, h3 { font-family: 'Inter', sans-serif; color: #2c3e50; }
    </style>
    """, unsafe_allow_html=True)




# --- Inicialização do Session State ---
if 'analisado' not in st.session_state:
    st.session_state.analisado = False
if 'resultados' not in st.session_state:
    st.session_state.resultados = {}
if 'atleta_dados' not in st.session_state:
    st.session_state.atleta_dados = {}

# --- FUNÇÕES AUXILIARES ---
# --- FUNÇÕES AUXILIARES ---

def validar_imagem(uploaded_file):
    """Verifica se o arquivo é seguro, menor que 5MB e realmente é uma imagem."""
    if uploaded_file is None:
        return None
    
    # 1. Verifica o tamanho (Máximo 5MB)
    if uploaded_file.size > 5 * 1024 * 1024:
        st.error("⚠️ O arquivo é muito grande. O tamanho máximo permitido é 5MB.")
        return None
        
    # 2. Verifica a integridade do arquivo
    try:
        img = Image.open(uploaded_file)
        img.verify() # Confirma se a estrutura interna é de imagem
        uploaded_file.seek(0) # Reseta a leitura para o gerador de PDF conseguir usar depois
        return uploaded_file
    except UnidentifiedImageError:
        st.error("🚨 Arquivo inválido ou corrompido. Por favor, envie uma imagem real (PNG/JPG).")
        return None
    except Exception as e:
        st.error(f"⚠️ Erro ao processar a imagem: {e}")
        return None

def render_premium_card(chave, info, res_finais, interpreter):
    z_score = res_finais.get(f'Z_{chave}', 0)
    p_score = res_finais.get(f'P_{chave}', 50)
    
    cor = info['cor']
    classe_txt = info['titulo_card'] 
    
    st.markdown(f"### <span style='color:{cor}'>{classe_txt}</span>", unsafe_allow_html=True)
    st.caption(f"💡 *O que isso mede: {info['subtitulo']}*")
    st.markdown(f"**Score:** `{p_score:.0f}/100`")
    
    fig_gauge = interpreter.plot_gauge_performance(z_score, "")
    st.pyplot(fig_gauge)
    
    st.write(info['texto'])
    st.markdown("---")

# --- FUNÇÕES DO CARROSSEL (AGORA BANNER ESTÁTICO) ---
def get_base64_of_image(file_path):
    """Lê a imagem física e transforma em código de texto (Base64)"""
    try:
        with open(file_path, "rb") as f:
            data = f.read()
        return base64.b64encode(data).decode()
    except Exception as e:
        return "" 

def render_banner_carrossel():
    """Injeta o HTML/CSS de um banner estático e seguro no topo da página"""
    # Lê apenas a primeira imagem da pasta
    img_base64 = get_base64_of_image('assets/pg_salto.png')

    # Se faltar a imagem, cancela silenciosamente sem quebrar o software
    if not img_base64:
        return

    # O CSS agora é super simples, sem 'position: absolute', o que impede de sobrepor os botões!
    html_code = f"""
    <style>
    /* 1. Padrão: Computador (Desktop) */
    .banner-estatico {{
        width: 100%;
        height: 500px; 
        object-fit: cover;
        border-radius: 12px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        margin-bottom: 25px;
        display: block; /* Garante que empurre os elementos de baixo */
    }}

    /* 2. Regra de Responsividade: Celulares e Tablets */
    @media (max-width: 768px) {{
        .banner-estatico {{
            height: 250px; 
            margin-bottom: 15px;
        }}
    }}
    </style>
    
    <img class="banner-estatico" src="data:image/png;base64,{img_base64}" alt="Banner Principal">
    """
    st.markdown(html_code, unsafe_allow_html=True)


# --- FUNÇÃO DE GRUPO ATUALIZADA (LÓGICA DE REFERÊNCIA) ---
# 1. Certifique-se de que o import no topo do arquivo app.py inclua:
# from src.pdf_generator import criar_pdf, criar_relatorio_grupo

# --- FUNÇÃO DE GRUPO ATUALIZADA (COM NOME DA EQUIPE) ---
def render_interface_grupo(df_ref):
    """
    Renderiza a interface de processamento em lote com Upload de Logo e Persistência de Dados.
    """
    st.header("📂 Análise de Performance de Grupo")
    
    # --- 1. CONFIGURAÇÃO E UPLOAD ---
    # Layout inspirado no PDF: Tabela + Controles + Logo 
    
    with st.expander("📝 Instruções e Entrada de Dados", expanded=True):
        st.markdown("""
        <div style='background-color: #e8f4f8; padding: 15px; border-radius: 10px; border-left: 5px solid #2980b9;'>
            <small><b>Instruções:</b> Cole os dados do Excel abaixo. O sistema fará a sugestão automaticamente[cite: 3].</small>
        </div>
        """, unsafe_allow_html=True)
        
        # Configuração das colunas da tabela
        template_data = pd.DataFrame(columns=["ID", "Nome", "Sexo", "Idade", "Peso (kg)", "Altura (cm)", "R", "Xc"])
        
        # 2. Configuramos as colunas (Removi a linha do PhA daqui também)
        config_colunas = {
            "Sexo": st.column_config.SelectboxColumn("Sexo", options=["Masculino", "Feminino"], required=True, width="medium"),
            "ID": st.column_config.TextColumn("ID", width="small"),
            "Nome": st.column_config.TextColumn("Nome", width="large"),
            "Idade": st.column_config.NumberColumn("Idade", min_value=10, max_value=100),
            "Peso (kg)": st.column_config.NumberColumn("Peso (kg)", min_value=30.0, max_value=200.0),
            "Altura (cm)": st.column_config.NumberColumn("Altura (cm)", min_value=100.0, max_value=250.0),
            "R": st.column_config.NumberColumn("R (Ω) - 50kHz", help="Resistência pura medida no aparelho"),
            "Xc": st.column_config.NumberColumn("Xc (Ω) - 50kHz", help="Reatância pura medida no aparelho"),
        }

        df_input = st.data_editor(
            template_data,
            num_rows="dynamic",
            column_config=config_colunas,
            use_container_width=True,
            hide_index=True
        )

    st.write("---")
    
    # --- 2. CONTROLES E LOGO (Área de Ação) ---
    c1, c2, c3 = st.columns([2, 1.5, 1.5])
    
    with c1:
        # Nome da Equipe [cite: 21]
        nome_equipe = st.text_input("Nome da Equipe / Clube:", value="Xingu FC", placeholder="Ex: Xingu FC")
    
    with c2:
        # Modo de Comparação [cite: 33]
        modo_comparacao = st.radio(
            "Comparar com:",
            ["🌍 Banco Global (Elite)", "🏠 Média do Grupo (Intra-Time)"],
            horizontal=False
        )
        
    with c3:
        # Upload do Logotipo [cite: 37, 41]
        # Isso é crucial para passar para o PDF_Generator depois
        # Upload do Logotipo
        logo_upload_raw = st.file_uploader("Logotipo do Clube (Opcional)", type=["png", "jpg", "jpeg"])
        logo_upload = validar_imagem(logo_upload_raw) if logo_upload_raw else None

    # --- 3. PROCESSAMENTO (Botão de Ação) [cite: 42] ---
    # Usamos um callback ou verificamos o clique para salvar no session_state
    if st.button("🚀 PROCESSAR GRUPO", type="primary", use_container_width=True):
        if df_input.empty or df_input.dropna(how='all').empty:
            st.error("⚠️ A tabela está vazia!")
        else:
            with st.spinner(f"Processando atletas do {nome_equipe}..."):
                # A. Tratamento de Dados
                df_proc = df_input.copy()
                cols_num = ['Idade', 'Peso (kg)', 'Altura (cm)', 'R', 'Xc']
                for c in cols_num:
                    if df_proc[c].dtype == object:
                        df_proc[c] = df_proc[c].astype(str).str.replace(',', '.', regex=False)
                    df_proc[c] = pd.to_numeric(df_proc[c], errors='coerce').fillna(0)

                mapa_sexo = {"Masculino": 1, "Feminino": 0, "M": 1, "F": 0}
                df_proc['SEXO'] = df_proc['Sexo'].map(mapa_sexo).fillna(0).astype(int)
                df_proc = df_proc.rename(columns={'Idade': 'AGE', 'Peso (kg)': 'WEIGHT', 'Altura (cm)': 'HEIGHT'})

                # B. Cálculo via API (Em Paralelo para Alta Performance)
                from concurrent.futures import ThreadPoolExecutor, as_completed
                
                resultados_api = []
                total_atletas = len(df_proc)
                progresso = st.progress(0)
                
                # 1. Prepara a lista de todos os atletas primeiro
                lista_dados_atletas = []
                for idx, row in df_proc.iterrows():
                    dados_atleta = {
                        "ID": str(row.get('Nome', row.get('ID', f"Atleta_{idx}"))),
                        "SEXO": int(row.get('SEXO', 0)),
                        "AGE": float(row.get('AGE', 0)),
                        "HEIGHT": float(row.get('HEIGHT', 0)),
                        "WEIGHT": float(row.get('WEIGHT', 0)),
                        "R": float(row.get('R', 0)),
                        "Xc": float(row.get('Xc', 0))
                    }
                    lista_dados_atletas.append(dados_atleta)

                # 2. Dispara as requisições para a API simultaneamente (10 "caixas de banco" atendendo ao mesmo tempo)
                concluidos = 0
                with ThreadPoolExecutor(max_workers=10) as executor:
                    # Mapeia as tarefas
                    futuros = {executor.submit(chamar_api_bioms, atleta): atleta for atleta in lista_dados_atletas}
                    
                    # Conforme a API for respondendo (não importa a ordem), vamos salvando
                    for futuro in as_completed(futuros):
                        atleta_info = futuros[futuro]
                        try:
                            res = futuro.result()
                            if "erro" not in res:
                                resultados_api.append(res)
                            else:
                                st.warning(f"⚠️ Pulei o atleta {atleta_info['ID']}: {res['erro']}")
                        except Exception as e:
                            st.warning(f"⚠️ Falha na comunicação para o atleta {atleta_info['ID']}: {e}")
                        
                        # Atualiza a barra de progresso visual
                        concluidos += 1
                        progresso.progress(concluidos / total_atletas)

                # 3. Transformamos a lista de respostas da API em um DataFrame
                df_calculado = pd.DataFrame(resultados_api)

                # C. Estatísticas
                if df_calculado.empty:
                    st.error("❌ Nenhum dado foi processado pela API.")
                    st.stop()
                    
                if "Intra-Time" in modo_comparacao:
                    stats = BioMSStatistics(df_calculado) 
                else:
                    stats = BioMSStatistics(df_ref)

                # --- O PONTO QUE FALTAVA: Gerar os resultados com estatísticas ---
                resultados_finais = []
                for idx, row in df_calculado.iterrows():
                    atleta_dict = row.to_dict()
                    
                    # Aqui o sistema calcula Z-Score e Percentis para cada atleta
                    res_stats = stats.compare_athlete(atleta_dict)
                    
                    # Unimos os dados da API com os dados estatísticos
                    dados = {**atleta_dict, **res_stats}
                    
                    # Adicionamos a Label (Iniciais do nome) para os gráficos
                    nome = str(atleta_dict.get('ID', ''))
                    iniciais = "".join([n[0] for n in nome.split() if n])[:3].upper() if len(nome) > 2 else nome
                    dados['Label'] = iniciais
                    
                    resultados_finais.append(dados)
                
                # D. Salvar no Session State (Agora sim com os dados completos!)
                st.session_state['grupo_resultado'] = pd.DataFrame(resultados_finais)
                st.session_state['grupo_nome'] = nome_equipe
                st.session_state['grupo_modo'] = modo_comparacao

                st.success(f"✔ Análise concluída: {len(resultados_finais)} atletas processados via API.")

    # --- 4. EXIBIÇÃO DE RESULTADOS E RELATÓRIOS ---
    # Verifica se existe resultado processado na memória
    if 'grupo_resultado' in st.session_state:
        df_final = st.session_state['grupo_resultado']
        nome_atual = st.session_state['grupo_nome']
        
        st.write("---")
        
        # --- ÁREA DO RELATÓRIO PDF ---
        col_pdf_info, col_pdf_btn = st.columns([3, 1])
        with col_pdf_info:
            st.info("📄 O relatório completo inclui capas, rankings comparativos e fichas individuais de todos os atletas.")
        
        with col_pdf_btn:
            if PDF_AVAILABLE:
                # Lógica de Geração do PDF
                # Precisamos regenerar o PDF a cada clique para garantir que a logo (se houver no upload atual) seja usada
                # Se o usuário processou, a logo está em 'logo_upload' (se não recarregou a página)
                
                interp_pdf = BioMSInterpreter()
                disclaimer_pdf = interp_pdf.get_context_disclaimer()
                if "Intra-Time" in st.session_state['grupo_modo']:
                    disclaimer_pdf['titulo'] += " (REFERÊNCIA: INTRA-GRUPO)"

                # Chama a função que você definiu no final do seu código
                # Passamos o logo_upload diretamente
                try:
                    pdf_bytes = criar_relatorio_grupo(
                        df_final, 
                        interp_pdf, 
                        disclaimer_pdf, 
                        nome_equipe=nome_atual, 
                        logo_file=logo_upload # Passando o arquivo carregado 
                    )

                    st.download_button(
                        label="📥 BAIXAR RELATÓRIO (PDF)",
                        data=pdf_bytes,
                        file_name=f"BioMS_Relatorio_{nome_atual.replace(' ', '_')}.pdf",
                        mime="application/pdf",
                        use_container_width=True
                    )
                except Exception as e:
                    st.error(f"Erro ao gerar PDF: {e}")
            else:
                st.warning("Módulo PDF não disponível.")

        # --- DASHBOARD DE DADOS ---
        # Abas conforme visualizado no PDF [cite: 24]
        tab1, tab2 = st.tabs(["📊 Distribuição Z-Score", "📋 Tabela de Dados"])
        
        with tab1:
            st.subheader(f"Desempenho ao longo do tempo: {nome_atual}") # [cite: 43]
            st.caption("Z-Score 0 representa a média. Barras à esquerda indicam valores acima da referência.") # [cite: 44]
            
            interp_graf = BioMSInterpreter()
            # Gráficos de barra horizontal (Altair ou Matplotlib)
            metrics = [
                ('Z_BioMS_8', 'Eficiência Metabólica (BioMS-8)'), # [cite: 70]
                ('Z_BioMS_1', 'Capacidade Estrutural (BioMS-1)'), # [cite: 71]
                ('Z_BioMS_5', 'Potência Contrátil (BioMS-5)'),    # [cite: 83]
                ('Z_BioMS_9', 'Resiliência e Velocidade (BioMS-9)') # [cite: 105]
            ]
            
            for metrica, titulo in metrics:
                if metrica in df_final.columns:
                    # Renderiza o gráfico usando sua função existente
                    fig = interp_graf.plot_ranking_batch(df_final, metrica, titulo)
                    
                    # Colocamos o gráfico dentro de colunas para limitar a largura máxima dele na tela
                    col_espaco1, col_grafico, col_espaco2 = st.columns([0.99, 9, 0.99]) 
                    with col_grafico:
                        # O use_container_width=True faz ele respeitar os limites da coluna 'col_grafico'
                        st.pyplot(fig, use_container_width=True)
                    
        with tab2:
            st.dataframe(df_final.style.format("{:.2f}", subset=[c for c in df_final.columns if df_final[c].dtype == 'float64']), use_container_width=True)



# --- FUNÇÃO NOVA: Z-SCORE UNIVERSAL (ATUALIZADA) ---
def render_interface_zscore_universal():
    st.header("📈 Módulo de Z-Score Universal")
    st.markdown("Calcule rapidamente o Z-Score para **qualquer teste físico ou métrica** e gere rankings comparativos da sua equipe.")
    
    with st.expander("⚙️ Configuração do Teste & Personalização", expanded=True):
        c1, c2 = st.columns([2, 1])
        with c1:
            nome_teste = st.text_input("Nome da Variável / Teste:", placeholder="Ex: Salto Vertical (CMJ), Sprint 10m...")
        with c2:
            direcao = st.radio("Lógica do Teste:", ["🔼 Maior é melhor (Ex: Salto)", "🔽 Menor é melhor (Ex: Tempo)"])
        
        st.write("---")
        st.markdown("<small><b>🎨 Personalização Visual (Premium)</b></small>", unsafe_allow_html=True)
        cor1, cor2, logo_col = st.columns([1, 1, 2])
        with cor1:
            cor_pos = st.color_picker("Cor Acima da Média", "#69FF89")
        with cor2:
            cor_neg = st.color_picker("Cor Abaixo da Média", "#bc88ff")
        with logo_col:
            logo_raw_z = st.file_uploader("Logo do Cliente (Opcional)", type=["png", "jpg"])
            logo_upload_z = validar_imagem(logo_raw_z) if logo_raw_z else None
            
        st.markdown("<small><b>Cole os dados (Nome e Valor) abaixo:</b></small>", unsafe_allow_html=True)
        
        df_template = pd.DataFrame(columns=["Nome do Atleta", "Valor do Teste"])
        config_colunas = {
            "Nome do Atleta": st.column_config.TextColumn("Nome", width="large", required=True),
            "Valor do Teste": st.column_config.NumberColumn("Valor", width="medium", required=True)
        }
        
        df_input = st.data_editor(df_template, num_rows="dynamic", column_config=config_colunas, use_container_width=True, hide_index=True)

    if st.button("📊 GERAR RANKING CUSTOMIZADO", type="primary"):
        df_calc = df_input.dropna(how='any').copy()
        
        if df_calc.empty or len(df_calc) < 2:
            st.error("⚠️ Insira pelo menos 2 atletas para calcular a média e o desvio padrão.")
            return
            
        if not nome_teste: nome_teste = "Teste Customizado"

        with st.spinner("Calculando e gerando design..."):
            media = df_calc["Valor do Teste"].mean()
            desvio = df_calc["Valor do Teste"].std(ddof=1)
            
            if desvio == 0:
                st.warning("Todos possuem exatamente o mesmo valor.")
                return
            
            df_calc["Z_Score"] = (df_calc["Valor do Teste"] - media) / desvio
            if "Menor" in direcao:
                df_calc["Z_Score"] = df_calc["Z_Score"] * -1
            
            df_calc["Label"] = df_calc["Nome do Atleta"]
            
            # Manipulação segura da Logo Temporária
            logo_path = None
            if logo_upload_z:
                import tempfile
                ext = os.path.splitext(logo_upload_z.name)[1]
                with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
                    tmp.write(logo_upload_z.getvalue())
                    logo_path = tmp.name

            # Renderização passando as cores e a logo
            interp_graf = BioMSInterpreter()
            fig = interp_graf.plot_ranking_batch(df_calc, "Z_Score", f"Ranking: {nome_teste}", cor_positiva=cor_pos, cor_negativa=cor_neg, logo_path=logo_path)
            
            st.success(f"Cálculo concluído! Média do grupo: {media:.2f}")
            
            col_espaco1, col_grafico, col_espaco2 = st.columns([0.5, 9, 0.5]) 
            with col_grafico:
                st.pyplot(fig, use_container_width=True)
            
            # --- DOWNLOAD DO PDF ---
            if PDF_AVAILABLE:
                st.write("---")
                try:
                    pdf_bytes = criar_relatorio_zscore_universal(df_calc, nome_teste, fig, logo_path)
                    st.download_button(
                        label="📥 BAIXAR RELATÓRIO DO TESTE (PDF)",
                        data=pdf_bytes,
                        file_name=f"BioMS_{nome_teste.replace(' ', '_')}.pdf",
                        mime="application/pdf",
                        use_container_width=True
                    )
                except Exception as e:
                    st.error(f"Erro ao gerar PDF: {e}")

            st.subheader("📋 Tabela de Dados Calculada")
            st.dataframe(df_calc[["Nome do Atleta", "Valor do Teste", "Z_Score"]].style.format({"Valor do Teste": "{:.2f}", "Z_Score": "{:.2f}"}), use_container_width=True)

            # Limpeza do arquivo temporário da logo
            if logo_path and os.path.exists(logo_path):
                try: os.remove(logo_path)
                except: pass

# --- FUNÇÃO NOVA: AVALIAÇÃO NORMATIVA (LONGITUDINAL E 1RM) ---
def render_interface_normativa():
    st.header("📊 Avaliação Normativa & Evolução (1RM)")
    st.markdown("Acompanhe o progresso do aluno. O sistema calcula automaticamente o 1RM para exercícios de carga (Fórmula de Epley).")
    
    lista_exercicios = obter_lista_exercicios()
    if not lista_exercicios:
        st.error("⚠️ Não foi possível carregar a lista de exercícios da API.")
        return

    with st.expander("👤 Dados do Aluno & Personalização", expanded=True):
        c1, c2, c3 = st.columns([2, 1, 1])
        with c1: nome = st.text_input("Nome do Aluno:", "Aluno Exemplo")
        with c2: sexo = st.selectbox("Sexo:", ["Feminino", "Masculino"])
        with c3: idade = st.number_input("Idade:", 18, 90, 30)
        
        st.write("---")
        cor_col, logo_col = st.columns([1, 2])
        with cor_col: cor_aluno = st.color_picker("Cor das Barras do Aluno:", "#8b5cf6")
        with logo_col: 
            logo_raw_n = st.file_uploader("Logo do Treinador/Academia (Opcional)", type=["png", "jpg"])
            logo_upload = validar_imagem(logo_raw_n) if logo_raw_n else None
            
        st.write("---")
        st.markdown("<small><b>Insira as coletas abaixo. Para calcular 1RM, digite a Carga e as Repetições.</b></small>", unsafe_allow_html=True)
        
        # Tabela dinâmica preparada para longo prazo
        df_template = pd.DataFrame([
            {"Exercício": lista_exercicios[0], "Data": "01/01/2026", "Carga (kg)": 40.0, "Repetições": 10}
            
        ])
        
        config_colunas = {
            "Exercício": st.column_config.SelectboxColumn("Exercício", options=lista_exercicios, required=True, width="medium"),
            "Data": st.column_config.TextColumn("Data (ex: Jan/26)", required=True, width="small"),
            "Carga (kg)": st.column_config.NumberColumn("Carga (kg)", min_value=0.0, format="%.1f", width="small"),
            "Repetições": st.column_config.NumberColumn("Repetições", min_value=0, step=1, width="small")
        }
        
        df_input = st.data_editor(df_template, num_rows="dynamic", column_config=config_colunas, use_container_width=True, hide_index=True)

    if st.button("🚀 GERAR RELATÓRIO DE PROGRESSO", type="primary"):
        df_calc = df_input.dropna(subset=["Exercício", "Data"]).copy()
        
        if df_calc.empty:
            st.error("⚠️ Preencha pelo menos uma coleta.")
            return

        with st.spinner("Calculando estimativas de 1RM e gerando gráficos..."):
            
            # --- MOTOR DE INTELIGÊNCIA (CÁLCULO DE 1RM) ---
            valores_finais = []
            for idx, row in df_calc.iterrows():
                exe = row["Exercício"]
                carga = float(row.get("Carga (kg)", 0))
                reps = int(row.get("Repetições", 0))
                
                # Se o exercício é de repetição livre (Flexão, Abdominal), ignoramos a carga
                if "Reps" in exe or "Abdominal" in exe:
                    val = float(reps)
                else:
                    # Fórmula de Epley para 1RM (Força Máxima)
                    if reps > 1:
                        val = carga * (1 + 0.0333 * reps)
                    elif reps == 1:
                        val = carga
                    else:
                        val = 0
                
                valores_finais.append(val)
            
            df_calc["Valor_Final"] = valores_finais
            
            # --- TRATAMENTO DA LOGO DO TREINADOR ---
            logo_path = None
            if logo_upload:
                import tempfile
                ext = os.path.splitext(logo_upload.name)[1]
                with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
                    tmp.write(logo_upload.getvalue())
                    logo_path = tmp.name

            st.write("---")
            st.subheader(f"Evolução: {nome} ({idade} anos)")
            
            interp_graf = BioMSInterpreter()
            
            # --- AGRUPAR E PLOTAR OS GRÁFICOS ---
            # Identifica quais exercícios diferentes o treinador preencheu
            exercicios_unicos = df_calc["Exercício"].unique()
            
            # Vamos guardar os dados finais na memória para depois mandarmos para o PDF!
            st.session_state['dados_pdf_normativo'] = []
            
            for exe in exercicios_unicos:
                # Isola as linhas (coletas) apenas deste exercício
                df_exe = df_calc[df_calc["Exercício"] == exe].copy()
                
                # Consulta a API para pegar a média sem ver a tabela secreta!
                resposta_api = consultar_media_normativa(exe, sexo, idade)
                if "erro" in resposta_api:
                    st.warning(f"Sem dados normativos na literatura para {exe}.")
                    continue
                
                media_oficial = resposta_api["media"]
                
                # Desenha o gráfico longitudinal
                fig = interp_graf.plot_longitudinal_evolution(df_exe, media_oficial, exe, cor_aluno)
                
                # Layout de Exibição: Gráfico à esquerda, Tabela à direita
                col_graf, col_tab = st.columns([7, 3])
                
                with col_graf:
                    st.pyplot(fig, use_container_width=True)
                
                with col_tab:
                    st.markdown(f"**Detalhes ({exe}):**")
                    # Tabela limpa para o cliente visualizar
                    df_view = df_exe[["Data", "Carga (kg)", "Repetições", "Valor_Final"]].copy()
                    df_view.rename(columns={"Valor_Final": "Score / 1RM"}, inplace=True)
                    st.dataframe(df_view.style.format({"Carga (kg)": "{:.1f}", "Score / 1RM": "{:.1f}"}), hide_index=True)
                    
                    # Cálculo de Evolução Percentual!
                    progresso_txt = ""
                    if len(df_exe) > 1:
                        primeiro = df_exe.iloc[0]["Valor_Final"]
                        ultimo = df_exe.iloc[-1]["Valor_Final"]
                        if primeiro > 0:
                            progresso = ((ultimo - primeiro) / primeiro) * 100
                            cor_prog = "green" if progresso >= 0 else "red"
                            sinal = "+" if progresso >= 0 else ""
                            progresso_txt = f"{sinal}{progresso:.1f}%"
                            st.markdown(f"📈 **Evolução:** <span style='color:{cor_prog}'><b>{progresso_txt}</b></span>", unsafe_allow_html=True)

                st.write("---")
                
                # Salva o pacote deste exercício na memória para o Passo 3 (PDF)
                st.session_state['dados_pdf_normativo'].append({
                    "exercicio": exe,
                    "df": df_exe,
                    "media_grupo": media_oficial,
                    "figura": fig,
                    "evolucao": progresso_txt
                })

            # --- DOWNLOAD DO PDF ---
            if PDF_AVAILABLE and len(st.session_state['dados_pdf_normativo']) > 0:
                st.write("---")
                try:
                    pdf_bytes = criar_relatorio_normativo_longitudinal(
                        nome, 
                        idade, 
                        st.session_state['dados_pdf_normativo'], 
                        logo_path
                    )
                    st.download_button(
                        label="📥 BAIXAR RELATÓRIO DE PROGRESSO (PDF)",
                        data=pdf_bytes,
                        file_name=f"Evolucao_1RM_{nome.replace(' ', '_')}.pdf",
                        mime="application/pdf",
                        use_container_width=True
                    )
                except Exception as e:
                    st.error(f"Erro ao gerar PDF: {e}")

# --- MAIN ---
def main():
    # 1. Carregamento do Banco
    try:
        df_ref = load_data()
    except Exception as e:
        st.error(f"Erro ao carregar banco: {e}")
        st.stop()

    if df_ref.empty:
        st.warning("Banco vazio. Execute 'build_db.py'.")
        # st.stop() # Comentado para permitir teste se banco falhar, mas ideal é parar.

    # --- SIDEBAR GLOBAL ---
    with st.sidebar:
        if os.path.exists("logo.svg"):
            st.image("logo.svg", width=180)
        else:
            st.title("🧬 BioMS Pro")
            
        # SELETOR DE MODO
        # SELETOR DE MODO
        modo_analise = st.radio(
            "Modo de Análise", 
            [
                "📈 Índices BioMS", 
                "📈 Índices BioMS para Grupos/Equipes", 
                "📈 Testes Z-Score Universais", 
                "📈 Avaliação de Treinamento de Força",
                "📈 Avaliação de Corrida"
            ],
            help="Escolha o tipo de análise que deseja realizar."
        )
        st.markdown("---")

        #  INSERIR ESTE BLOCO AQUI 
        with st.expander("📜 Termos de Uso e Privacidade"):
            st.markdown("""
            **1. Isenção:** O BioMS é uma ferramenta de apoio à decisão esportiva. Não substitui avaliações clínicas.
            
            **2. LGPD:** O Treinador atua como **Controlador** e garante ter o consentimento do aluno. O BioMS é apenas o **Operador** técnico.
            
            **3. Privacidade:** O BioMS não armazena, retém ou comercializa os dados sensíveis inseridos. Eles existem apenas na memória temporária para gerar o relatório.
            """)
        #  FIM DO BLOCO INSERIDO 

    # =========================================================
    # CHAMA O CARROSSEL (ELE APARECERÁ NO TOPO DA TELA)
    # =========================================================
    render_banner_carrossel()


    # =========================================================
    # FLUXO 1: MODO INDIVIDUAL
    # =========================================================
    if modo_analise == "📈 Índices BioMS":
        
        # 1. Formulário na Sidebar (Limpo e Direto)
        with st.sidebar:
            st.header("⚙️ Configuração")
            with st.form("form_dados"):
                atleta_nome = st.text_input("Nome do Atleta/Usuário", value="Atleta Exemplo")
                
                c1, c2 = st.columns(2)
                sexo_map = {"Feminino": 0, "Masculino": 1}
                sexo = c1.selectbox("Sexo", list(sexo_map.keys()))
                idade = c2.number_input("Idade", 10, 100, 30)

                st.subheader("📏 Antropometria")
                h = st.number_input("Altura (cm)", 100.0, 250.0, 175.0, step=0.5)
                w = st.number_input("Peso (kg)", 30.0, 200.0, 75.0, step=0.1)

                st.subheader("⚡ Bioimpedância (50kHz)")
                vc1, vc2 = st.columns(2)
                r_input = vc1.number_input("R (Ω)", 100.0, 1500.0, 500.0)
                xc_input = vc2.number_input("Xc (Ω)", 10.0, 200.0, 55.0)

                st.markdown("###")
                btn_analisar = st.form_submit_button("ANALISAR PERFORMANCE 🚀", type="primary")

                aceite_termos = st.checkbox("☑️ Declaro ter consentimento do aluno para calcular as métricas e concordo com os Termos (o BioMS não armazena estes dados).")

            

        # 2. Lógica de Processamento Individual (Conectada à API)
        if btn_analisar:
            
            # 👇 INSERIR A TRAVA AQUI 👇
            if not aceite_termos:
                st.sidebar.error("⚠️ Obrigatório: Marque a caixa de consentimento acima do botão para continuar.")
            else:
                # 👇 SE ELE ACEITOU, EXECUTA O SEU CÓDIGO NORMAL (Não esqueça de indentar tudo isso para a direita!) 👇
                
                # Montamos o pacote de dados para a API
                atleta_atual = {
                    'ID': atleta_nome, 
                    'SEXO': sexo_map[sexo], 
                    'AGE': idade,
                    'HEIGHT': h, 
                    'WEIGHT': w, 
                    'R': r_input, 
                    'Xc': xc_input
                }

                # Chamadas de suporte (Estatística e Interpretação)
                stats = BioMSStatistics(df_ref)
                interpreter = BioMSInterpreter()

                # O grande momento: Chamada da API
                with st.spinner("Calculando via API..."):
                    res_atleta = chamar_api_bioms(atleta_atual)
                
                # Comparação estatística e geração de relatório
                res_finais = stats.compare_athlete(res_atleta)
                relatorio_dict = interpreter.gerar_relatorio_inteligente(res_finais)

                # Salva no estado da sessão para exibição
                st.session_state.analisado = True
                st.session_state.atleta_dados = atleta_atual
                st.session_state.res_finais = res_finais
                st.session_state.relatorio_dict = relatorio_dict
                st.session_state.interpreter = interpreter

        # Exibição dos Resultados Individuais
        if st.session_state.analisado:
            atleta = st.session_state.atleta_dados
            res = st.session_state.res_finais
            rel_dict = st.session_state.relatorio_dict
            interp = st.session_state.interpreter

            st.title(f"BioMS Report: {atleta['ID']}")
            
            disclaimer = interp.get_context_disclaimer()
            st.markdown(f"""
            <div style="background-color: #f8f9fa; border-left: 4px solid #f39c12; padding: 15px; margin-bottom: 20px; border-radius: 5px;">
                <h4 style="margin-top: 0; color: #2c3e50;">💡 {disclaimer['titulo']}</h4>
                <p style="margin-bottom: 0; color: #555555; font-size: 14px;">{disclaimer['texto']}</p>
            </div>
            """, unsafe_allow_html=True)

            k1, k2, k3, k4 = st.columns(4)

            def safe_p(k): return res.get(f'P_{k}', 50)
            
            k1.metric("Eficiência (BioMS-8)", f"{safe_p('BioMS_8'):.0f}/100", help="Custo energético e arrasto metabólico.")
            k2.metric("Estrutura (BioMS-1)", f"{safe_p('BioMS_1'):.0f}/100", help="Volume de massa muscular (Chassi).")
            k3.metric("Resiliência (BioMS-9)", f"{safe_p('BioMS_9'):.0f}/100", help="Integridade da membrana celular (Suspensão).")
            k4.metric("Potência (BioMS-5)", f"{safe_p('BioMS_5'):.0f}/100", help="Capacidade de explosão e velocidade (Motor).")
            st.markdown("---")

            col_left, col_right = st.columns([1, 1.2])

            with col_left:
                st.subheader("Matriz de Performance")
                fig_radar = interp.plot_radar_chart(res) 
                st.pyplot(fig_radar)
                
                if PDF_AVAILABLE:
                    with st.spinner("Gerando PDF..."):
                        try:
                            pdf_data = criar_pdf(atleta, res, rel_dict, fig_radar, disclaimer)
                            st.download_button(
                                "📥 Baixar Relatório (PDF)", 
                                pdf_data, 
                                f"BioMS_{atleta['ID']}.pdf", 
                                "application/pdf", 
                                use_container_width=True
                            )
                        except Exception as e:
                            st.error(f"Erro ao gerar PDF: {e}")

            with col_right:
                st.subheader("Diagnóstico de Engenharia Corporal")
                ordem = [('BioMS_8', "🔥 Eficiência"), ('BioMS_1', "💪 Estrutura"), 
                         ('BioMS_9', "⚡ Resiliência"), ('BioMS_5', "🚀 Potência")]

                for chave, label in ordem:
                    with st.expander(f"{label} (Detalhes)", expanded=(chave == 'BioMS_8')):
                        render_premium_card(chave, rel_dict[chave], res, interp)
        else:
            st.markdown("<h3 style='text-align: center;'>Análise Individual</h3>", unsafe_allow_html=True)
            st.info("👈 Preencha os dados na barra lateral para iniciar.")

    # =========================================================
    # FLUXO 2: MODO GRUPO / TIME (NOVO)
    # =========================================================
    elif modo_analise == "📈 Índices BioMS para Grupos/Equipes":
        render_interface_grupo(df_ref)

    # =========================================================
    # FLUXO 3: Z-SCORE UNIVERSAL
    # =========================================================
    elif modo_analise == "📈 Testes Z-Score Universais":
        render_interface_zscore_universal()

# =========================================================
    # FLUXO 4: AVALIAÇÃO NORMATIVA (PERCENTIS)
    # =========================================================
    elif modo_analise == "📈 Avaliação de Treinamento de Força":
        render_interface_normativa()

# =========================================================
    # FLUXO 5: MÓDULO DE CORRIDA (BIOMS RUNNERS)
    # =========================================================
    elif modo_analise == "📈 Avaliação de Corrida":
        st.header("🏃‍♂️ BioMS Runners - Avaliação de Performance")
        
        # O Sub-menu Inteligente para SaaS (Atualizado)
        modo_runner = st.radio(
            "Selecione o tipo de análise:", 
            [
                "👤 Individual (Transversal e Evolução)", 
                "👥 Equipe (Ranking Transversal)",
                "👑 Evolução de Equipes (Premium)"
            ],
            horizontal=True
        )
        st.write("---")

        # ---------------------------------------------------------
        # CAMINHO A: INDIVIDUAL (Mantido intacto e perfeito)
        # ---------------------------------------------------------
        if "Individual" in modo_runner:
            st.markdown("Insira um único teste (Transversal) ou múltiplas datas (Longitudinal). O sistema calcula o seu **Score (Percentil)**, onde `50` é a média e números maiores significam maior velocidade.")
            
            with st.expander("👤 Dados do Atleta & Personalização", expanded=True):
                c1, c2, c3, c4 = st.columns([2, 1, 1, 1])
                with c1: nome_runner = st.text_input("Nome do Atleta:", "Atleta Runner")
                with c2: sexo_runner = st.selectbox("Sexo (Corrida):", ["Masculino", "Feminino"])
                with c3: idade_runner = st.number_input("Idade (Corrida):", 18, 90, 30)
                with c4: nivel = st.selectbox("Nível de Comparação:", ["Amador", "Elite"])
                
                st.write("---")
                cor_col, logo_col = st.columns([1, 2])
                with cor_col: cor_aluno = st.color_picker("Cor das Barras do Aluno:", "#3498db")
                with logo_col: 
                    logo_raw_r = st.file_uploader("Logo do Treinador/Equipe (Opcional)", type=["png", "jpg"], key="logo_runner")
                    logo_upload_runner = validar_imagem(logo_raw_r) if logo_raw_r else None
                    
                st.write("---")
                st.markdown("<small><b>Insira as coletas abaixo (Preencha Minutos e Segundos):</b></small>", unsafe_allow_html=True)
                
                # Tabela dinâmica
                df_template_runner = pd.DataFrame([
                    {"Distância": "5km", "Data": "01/01/2026", "Minutos": 28, "Segundos": 30}
                ])
                
                distancias_opcoes = ["100m", "400m", "1500m", "5km", "10km"]
                
                config_colunas_runner = {
                    "Distância": st.column_config.SelectboxColumn("Distância", options=distancias_opcoes, required=True, width="medium"),
                    "Data": st.column_config.TextColumn("Data (ex: Jan/26)", required=True, width="small"),
                    "Minutos": st.column_config.NumberColumn("Minutos", min_value=0, step=1, width="small"),
                    "Segundos": st.column_config.NumberColumn("Segundos", min_value=0, max_value=59, step=1, width="small")
                }
                
                df_input_runner = st.data_editor(df_template_runner, num_rows="dynamic", column_config=config_colunas_runner, use_container_width=True, hide_index=True, key="grid_runner")

            if st.button("🚀 GERAR RELATÓRIO DE CORRIDA", type="primary"):
                df_calc_runner = df_input_runner.dropna(subset=["Distância", "Data"]).copy()
                
                if df_calc_runner.empty:
                    st.error("⚠️ Preencha pelo menos uma coleta.")
                else:
                    with st.spinner("Calculando performance na API BioMS..."):
                        
                        valores_percentil = []
                        z_scores_visuais = []
                        tempos_formatados = []
                        erro_api = False 

                        for idx, row in df_calc_runner.iterrows():
                            dist = row["Distância"]
                            mins = int(row.get("Minutos", 0))
                            segs = int(row.get("Segundos", 0))
                            
                            tempo_total = (mins * 60) + segs
                            
                            if tempo_total <= 0:
                                valores_percentil.append(0)
                                z_scores_visuais.append(0)
                                tempos_formatados.append("00m 00s")
                                continue
                                
                            dados_req = {
                                "ID": nome_runner,
                                "distancia": dist,
                                "sexo": "M" if sexo_runner == "Masculino" else "F",
                                "idade": int(idade_runner),
                                "nivel": nivel,
                                "tempo_segundos": float(tempo_total)
                            }
                            
                            res_api = calcular_corrida_api(dados_req)
                            
                            if "erro" in res_api:
                                st.warning(f"Erro ao calcular {dist} em {row['Data']}: {res_api['erro']}")
                                valores_percentil.append(0)
                                z_scores_visuais.append(0)
                                tempos_formatados.append(f"{mins}m {segs}s")
                                erro_api = True
                            else:
                                z = res_api["z_score"]
                                p = res_api["percentil"]
                                valores_percentil.append(p)
                                z_scores_visuais.append(z * -1) # Inversão visual
                                tempos_formatados.append(f"{mins}m {segs}s")
                                
                        df_calc_runner["Valor_Final"] = valores_percentil 
                        df_calc_runner["Z_Score_Visual"] = z_scores_visuais
                        df_calc_runner["Tempo_Txt"] = tempos_formatados
                        
                        if not erro_api:
                            st.success("Cálculos concluídos com sucesso!")
                        
                        logo_path = None
                        if logo_upload_runner:
                            import tempfile
                            ext = os.path.splitext(logo_upload_runner.name)[1]
                            with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
                                tmp.write(logo_upload_runner.getvalue())
                                logo_path = tmp.name

                        st.write("---")
                        st.subheader(f"Evolução de Performance: {nome_runner} ({idade_runner} anos)")
                        
                        interp_graf = BioMSInterpreter()
                        distancias_unicas = df_calc_runner["Distância"].unique()
                        st.session_state['dados_pdf_corrida'] = []
                        
                        for dist in distancias_unicas:
                            df_dist = df_calc_runner[df_calc_runner["Distância"] == dist].copy()
                            media_oficial = 50.0 
                            
                            fig = interp_graf.plot_longitudinal_evolution(df_dist, media_oficial, f"Performance ({dist})", cor_aluno)
                            
                            col_graf, col_tab = st.columns([7, 3])
                            with col_graf:
                                st.pyplot(fig, use_container_width=True)
                            
                            with col_tab:
                                st.markdown(f"**Detalhes ({dist}):**")
                                df_view = df_dist[["Data", "Tempo_Txt", "Valor_Final"]].copy()
                                df_view.rename(columns={"Tempo_Txt": "Tempo", "Valor_Final": "Score (Percentil)"}, inplace=True)
                                st.dataframe(df_view.style.format({"Score (Percentil)": "{:.1f}%"}), hide_index=True)
                                
                                progresso_txt = ""
                                if len(df_dist) > 1:
                                    primeiro = df_dist.iloc[0]["Valor_Final"]
                                    ultimo = df_dist.iloc[-1]["Valor_Final"]
                                    if primeiro > 0:
                                        progresso = ((ultimo - primeiro) / primeiro) * 100
                                        cor_prog = "green" if progresso >= 0 else "red"
                                        sinal = "+" if progresso >= 0 else ""
                                        progresso_txt = f"{sinal}{progresso:.1f}%"
                                        st.markdown(f"📈 **Evolução do Score:** <span style='color:{cor_prog}'><b>{progresso_txt}</b></span>", unsafe_allow_html=True)

                            st.write("---")
                            
                            st.session_state['dados_pdf_corrida'].append({
                                "exercicio": dist,
                                "df": df_dist,
                                "media_grupo": media_oficial,
                                "figura": fig,
                                "evolucao": progresso_txt
                            })

                        if PDF_AVAILABLE and len(st.session_state['dados_pdf_corrida']) > 0:
                            try:
                                pdf_bytes = criar_relatorio_normativo_longitudinal(
                                    nome_runner, idade_runner, st.session_state['dados_pdf_corrida'], logo_path,
                                    titulo_relatorio="Relatório de Progresso e Performance de Corrida"
                                )
                                st.download_button(
                                    label="📥 BAIXAR RELATÓRIO DE CORRIDA (PDF)", data=pdf_bytes,
                                    file_name=f"Evolucao_Corrida_{nome_runner.replace(' ', '_')}.pdf", mime="application/pdf", use_container_width=True
                                )
                            except Exception as e:
                                st.error(f"Erro ao gerar PDF: {e}")

        # ---------------------------------------------------------
        # CAMINHO B: EQUIPE TRANSVERSAL (A NOVA MÁGICA)
        # ---------------------------------------------------------
        elif "Equipe" in modo_runner:
            st.markdown("Cole os dados da equipe para gerar o **Ranking de Performance**. O gráfico mostrará a distância de cada atleta em relação à média (Linha Zero).")
            
            with st.expander("📝 Configuração e Dados da Equipe", expanded=True):
                c1, c2, c3 = st.columns([2, 1.5, 1.5])
                with c1: nome_equipe_run = st.text_input("Nome da Equipe:", "Runners Club")
                with c2: 
                    modo_comp_run = st.radio("Comparar com:", ["🌍 Banco Global (Literatura)", "🏠 Média do Grupo (Intra-Time)"])
                with c3:
                    logo_raw_g = st.file_uploader("Logo da Equipe", type=["png", "jpg"], key="logo_run_g")
                    logo_upload_g = validar_imagem(logo_raw_g) if logo_raw_g else None

                st.write("---")
                
                df_template_grp = pd.DataFrame([
                    {"Nome": "João", "Sexo": "Masculino", "Idade": 25, "Nível": "Amador", "Distância": "5km", "Minutos": 24, "Segundos": 30},
                    {"Nome": "Maria", "Sexo": "Feminino", "Idade": 28, "Nível": "Amador", "Distância": "5km", "Minutos": 26, "Segundos": 15},
                ])
                
                config_cols_grp = {
                    "Nome": st.column_config.TextColumn("Atleta", required=True),
                    "Sexo": st.column_config.SelectboxColumn("Sexo", options=["Masculino", "Feminino"], required=True),
                    "Idade": st.column_config.NumberColumn("Idade", min_value=10, max_value=100),
                    "Nível": st.column_config.SelectboxColumn("Nível", options=["Amador", "Elite"]),
                    "Distância": st.column_config.SelectboxColumn("Distância", options=["100m", "400m", "1500m", "5km", "10km"], required=True),
                    "Minutos": st.column_config.NumberColumn("Minutos", min_value=0, step=1),
                    "Segundos": st.column_config.NumberColumn("Segundos", min_value=0, max_value=59, step=1)
                }
                
                df_input_grp = st.data_editor(df_template_grp, num_rows="dynamic", column_config=config_cols_grp, use_container_width=True, hide_index=True)
            
            if st.button("🚀 PROCESSAR RANKING DA EQUIPE", type="primary"):
                df_calc = df_input_grp.dropna(subset=["Nome", "Distância"]).copy()
                if df_calc.empty:
                    st.error("⚠️ Preencha os dados dos atletas.")
                else:
                    with st.spinner("Analisando performance da equipe..."):
                        resultados = []
                        
                        # --- MOTOR 1: COMPARAÇÃO INTRA-TIME ---
                        if "Intra-Time" in modo_comp_run:
                            distancias_unicas = df_calc["Distância"].unique()
                            for dist in distancias_unicas:
                                df_dist = df_calc[df_calc["Distância"] == dist].copy()
                                # Converte tudo para segundos para ter a base matemática
                                df_dist["Tempo_Seg"] = df_dist["Minutos"].fillna(0)*60 + df_dist["Segundos"].fillna(0)
                                
                                media_grp = df_dist["Tempo_Seg"].mean()
                                std_grp = df_dist["Tempo_Seg"].std(ddof=1)
                                
                                for idx, row in df_dist.iterrows():
                                    t = row["Tempo_Seg"]
                                    # Calcula Z-Score (invertido, pois menor tempo é melhor)
                                    if std_grp and std_grp > 0 and len(df_dist) > 1:
                                        z = (media_grp - t) / std_grp 
                                    else:
                                        z = 0
                                    
                                    resultados.append({
                                        "Nome do Atleta": row["Nome"],
                                        "Distância": dist,
                                        "Tempo_Txt": f"{int(row.get('Minutos',0))}m {int(row.get('Segundos',0))}s",
                                        "Valor do Teste": t, 
                                        "Z_Score": z,
                                        "Label": row["Nome"]
                                    })
                        
                        # --- MOTOR 2: COMPARAÇÃO GLOBAL (API) ---
                        else:
                            for idx, row in df_calc.iterrows():
                                t = row.get("Minutos",0)*60 + row.get("Segundos",0)
                                if t <= 0: continue
                                
                                req = {
                                    "ID": row["Nome"], "distancia": row["Distância"],
                                    "sexo": "M" if row["Sexo"]=="Masculino" else "F",
                                    "idade": int(row["Idade"]), "nivel": row["Nível"],
                                    "tempo_segundos": float(t)
                                }
                                res_api = calcular_corrida_api(req)
                                if "erro" not in res_api:
                                    # Inverte visualmente o Z-Score que veio da API
                                    z_visual = res_api["z_score"] * -1
                                    resultados.append({
                                        "Nome do Atleta": row["Nome"],
                                        "Distância": row["Distância"],
                                        "Tempo_Txt": f"{int(row.get('Minutos',0))}m {int(row.get('Segundos',0))}s",
                                        "Valor do Teste": t,
                                        "Z_Score": z_visual,
                                        "Label": row["Nome"]
                                    })
                                    
                        if not resultados:
                            st.error("Nenhum dado válido para calcular.")
                        else:
                            df_res = pd.DataFrame(resultados)
                            st.success("Cálculo concluído com sucesso!")
                            
                            logo_path = None
                            if logo_upload_g:
                                import tempfile
                                ext = os.path.splitext(logo_upload_g.name)[1]
                                with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
                                    tmp.write(logo_upload_g.getvalue())
                                    logo_path = tmp.name
                                    
                            interp = BioMSInterpreter()
                            
                            # Loop Inteligente: Gera 1 Ranking para CADA distância diferente encontrada na tabela!
                            for dist in df_res["Distância"].unique():
                                df_dist_res = df_res[df_res["Distância"] == dist].copy()
                                st.write("---")
                                st.subheader(f"🏆 Ranking de Performance: {dist}")
                                
                                # Gráfico Z-Score Global / Individual
                                fig = interp.plot_ranking_batch(df_dist_res, "Z_Score", f"Comparativo ({modo_comp_run.split(' ')[1]})")
                                st.pyplot(fig, use_container_width=True)
                                
                                # Tabela de Dados Exatos
                                with st.expander("📋 Ver Tabela de Tempos Exatos"):
                                    st.dataframe(df_dist_res[["Nome do Atleta", "Tempo_Txt", "Z_Score"]].style.format({"Z_Score": "{:.2f}"}), hide_index=True)
                                
                                # PDF usando o Z-Score Universal!
                                if PDF_AVAILABLE:
                                    try:
                                        pdf_bytes = criar_relatorio_zscore_universal(df_dist_res, f"Corrida {dist} - {nome_equipe_run}", fig, logo_path)
                                        st.download_button(
                                            label=f"📥 BAIXAR RELATÓRIO {dist} (PDF)", 
                                            data=pdf_bytes, 
                                            file_name=f"Ranking_{dist}_{nome_equipe_run.replace(' ', '_')}.pdf", 
                                            mime="application/pdf"
                                        )
                                    except Exception as e:
                                        st.error(f"Erro ao gerar PDF: {e}")

        # ---------------------------------------------------------
        # CAMINHO C: EQUIPE LONGITUDINAL (ISCA PREMIUM)
        # ---------------------------------------------------------
        elif "Premium" in modo_runner:
            st.info("🚀 **Recurso Premium:** Acompanhe a evolução de centenas de corredores ao longo de toda a temporada simultaneamente. Entre em contato para ativar este módulo no seu plano SaaS.")
if __name__ == "__main__":
    main()