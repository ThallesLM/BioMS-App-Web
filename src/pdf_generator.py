from fpdf import FPDF
import os
import tempfile
import matplotlib.pyplot as plt
from datetime import datetime

def clean_text(text):
    if not isinstance(text, str): return str(text)
    replacements = {'–': '-', '—': '-', '‘': "'", '’': "'", '“': '"', '”': '"', '…': '...', '•': '*'}
    for char, rep in replacements.items(): text = text.replace(char, rep)
    return text.encode('latin-1', 'ignore').decode('latin-1')

class PDFReport(FPDF):
    def __init__(self, orientation='P', unit='mm', format='A4'):
        super().__init__(orientation, unit, format)
        self.nome_equipe = ""
        self.is_group = False
        self.logo_custom_path = None 
        self.info_referencia = "" 

    def header(self):
        # --- 1. Logo do Sistema (Canto Superior Esquerdo - Padrão) ---
        logo_sys = "logo.png" if os.path.exists("logo.png") else None
        
        # Layout Específico para Grupo
        if self.is_group:
            # A. Texto Informativo (Esquerda)
            self.set_xy(10, 10)
            self.set_font('Arial', 'B', 14)
            self.set_text_color(44, 62, 80)
            self.cell(0, 6, clean_text(self.nome_equipe.upper()), 0, 1, 'L')
            
            self.set_font('Arial', '', 9)
            self.set_text_color(100, 100, 100)
            data_hoje = datetime.now().strftime("%d/%m/%Y")
            self.cell(0, 5, clean_text(f"Relatório Técnico | Data: {data_hoje}"), 0, 1, 'L')
            
            if self.info_referencia:
                self.set_font('Arial', 'I', 8)
                self.set_text_color(180, 50, 50)
                self.cell(0, 5, clean_text(f"Ref: {self.info_referencia}"), 0, 1, 'L')
            
            self.ln(2)
            self.set_font('Arial', '', 8)
            self.set_text_color(80, 80, 80)
            intro = "Análise BioMS: O novo padrão de mercado para análise de performance e saúdeatlética."
            self.multi_cell(130, 4, clean_text(intro), 0, 'L')

            # B. Logos (Direita - Lado a Lado)
            # Logo do Clube (Mais à esquerda do bloco direito) -> x=150
            if self.logo_custom_path and os.path.exists(self.logo_custom_path):
                try:
                    self.image(self.logo_custom_path, x=150, y=8, w=20)
                except: pass
            
            # Logo BioMS (Mais à direita) -> x=175
            if logo_sys:
                self.image(logo_sys, x=175, y=8, w=25)
            
            # Linha separadora
            self.set_y(40)
            self.set_draw_color(200, 200, 200)
            self.line(10, 38, 200, 38)

        else:
            # --- Cabeçalho Padrão (Individual) ---
            if logo_sys:
                self.image(logo_sys, x=85, y=8, w=40)
                self.ln(35)
            else:
                self.cell(0, 10, 'BioMS Technology', 0, 1, 'C')
                self.ln(5)

    def footer(self):
        self.set_y(-12)
        self.set_font('Arial', 'I', 8)
        self.set_text_color(150, 150, 150)
        rodape = clean_text(f'BioMS Analytics Pro | {self.nome_equipe} | Página {self.page_no()}')
        self.cell(0, 10, rodape, 0, 0, 'C')

# --- FUNÇÃO AUXILIAR 1: MODO INDIVIDUAL COMPLETO ---
def _desenhar_pagina_individual(pdf, atleta, res_finais, relatorio_dict, fig_radar, disclaimer):
    """Gera uma página completa por atleta (usado no botão Individual)"""
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)

    pdf.set_font('Arial', 'B', 14)
    pdf.set_text_color(44, 62, 80)
    nome = atleta.get('Nome', str(atleta.get('ID', 'Atleta')))
    pdf.cell(0, 10, clean_text(f"Relatório de Performance: {nome}"), 0, 1, 'C')
    pdf.ln(5)

    tmp_name = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            fig_radar.savefig(tmp.name, dpi=100, bbox_inches='tight')
            tmp_name = tmp.name
        pdf.image(tmp_name, x=60, w=90)
    except Exception as e:
        print(f"Erro ao gerar imagem no PDF: {e}")
    finally:
        # O 'Zelador': garante que o arquivo seja apagado de qualquer jeito
        if tmp_name and os.path.exists(tmp_name):
            os.remove(tmp_name)

    pdf.ln(5)

    pdf.set_font('Arial', '', 10)
    pdf.set_fill_color(240, 240, 240)
    metrics = ['BioMS_8', 'BioMS_1', 'BioMS_5', 'BioMS_9']
    labels = ['Eficiência Metabólica', 'Perfil Muscular', 'Explosão Muscular', 'Potencial de Velocidade']
    
    largura = 45
    pdf.set_x(15)
    for lb in labels: pdf.cell(largura, 8, clean_text(lb), 1, 0, 'C', fill=True)
    pdf.ln()
    pdf.set_x(15)
    pdf.set_font('Arial', '', 11)
    for m in metrics: pdf.cell(largura, 10, f"{res_finais.get(f'P_{m}',0):.0f}/100", 1, 0, 'C')
    pdf.ln(15)

    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 8, clean_text("Diagnóstico Técnico"), 0, 1, 'L')
    pdf.ln(2)
    for k in metrics:
        if k in relatorio_dict:
            info = relatorio_dict[k]
            pdf.set_font('Arial', 'B', 10)
            pdf.set_text_color(41, 128, 185)
            pdf.multi_cell(0, 5, clean_text(f"> {info['subtitulo']}: {info['titulo_card']}"), 0, 'L')
            pdf.set_font('Arial', '', 9)
            pdf.set_text_color(50, 50, 50)
            pdf.multi_cell(0, 5, clean_text(info['texto']), 0, 'J')
            pdf.ln(3)

# --- FUNÇÃO AUXILIAR 2: MODO GRUPO (Compacto + Diagnóstico Lateral) ---
def _desenhar_atleta_compacto(pdf, atleta, res_finais, relatorio_dict, fig_radar):
    """
    Desenha o atleta no fluxo contínuo da página com layout de 3 colunas:
    [Radar] | [Scores] | [Diagnóstico]
    """
    
    # Altura base estimada para um bloco
    altura_bloco = 60 
    if pdf.get_y() + altura_bloco > 270: 
        pdf.add_page()
    else:
        pdf.ln(3)
        pdf.set_draw_color(220, 220, 220)
        pdf.line(10, pdf.get_y(), 200, pdf.get_y())
        pdf.ln(5)

    # Guarda o Y inicial deste bloco para alinhar as colunas
    y_ini = pdf.get_y()

    # 1. Nome do Atleta (Cabeçalho do bloco)
    pdf.set_font('Arial', 'B', 11)
    pdf.set_text_color(0, 0, 0)
    nome = atleta.get('Nome', str(atleta.get('ID', 'Atleta')))
    pdf.cell(0, 6, clean_text(f"Atleta: {nome}"), 0, 1, 'L')

    # --- COLUNA 1: RADAR (Esquerda) ---
    tmp_name = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            fig_radar.set_size_inches(4, 4)
            fig_radar.savefig(tmp.name, dpi=80, bbox_inches='tight')
            tmp_name = tmp.name
        pdf.image(tmp_name, x=10, y=pdf.get_y(), w=45) # Radar ligeiramente menor
    except Exception as e:
        print(f"Erro ao gerar imagem no PDF compacto: {e}")
    finally:
        if tmp_name and os.path.exists(tmp_name):
            os.remove(tmp_name)

    # --- COLUNA 2: SCORES (Meio) ---
    # Posiciona à direita do radar
    pdf.set_xy(60, y_ini + 8)
    
    metrics = ['BioMS_8', 'BioMS_1', 'BioMS_5', 'BioMS_9']
    labels_map = {'BioMS_8': 'Eficiência Metabólica', 'BioMS_1': 'Perfil Muscular', 'BioMS_5': 'Explosão Muscular', 'BioMS_9': 'Potencial de Velocidade'}

    pdf.set_font('Arial', 'B', 8)
    for m in metrics:
        score = res_finais.get(f'P_{m}', 0)
        
        # Formatação de cores
        if score > 80: pdf.set_text_color(39, 174, 96) # Verde
        elif score < 40: pdf.set_text_color(192, 57, 43) # Vermelho
        else: pdf.set_text_color(0, 0, 0)
        
        pdf.set_x(60)
        label_curto = labels_map[m].split('/')[0] 
        pdf.cell(38, 5, clean_text(label_curto), 0, 0)
        pdf.cell(20, 5, f"{score:.0f}", 0, 1)

    # --- COLUNA 3: DIAGNÓSTICO (Direita) ---
    # Reseta o Y para o topo do bloco e move o X para a direita
    pdf.set_xy(130, y_ini + 8)
    
    pdf.set_font('Arial', 'B', 8)
    pdf.set_text_color(44, 62, 80)
    #pdf.cell(0, 5, clean_text("Classificação:"), 0, 1) # Título da coluna
    
    for m in metrics:
        if m in relatorio_dict:
            label_curto = labels_map[m].split('/')[0]
            diag_curto = relatorio_dict[m].get('titulo_card', '-')
            
            # Garante que o cursor X volte para a coluna da direita a cada linha
            pdf.set_x(120)
            
            # Imprime estilo "Métrica: Diagnóstico"
            pdf.set_font('Arial', 'B', 8)
            pdf.set_text_color(100, 100, 100) # Cinza no label
            pdf.cell(38, 4, clean_text(f"{label_curto}:"), 0, 0)
            
            pdf.set_font('Arial', '', 8)
            pdf.set_text_color(0, 0, 0) # Preto no valor
            pdf.cell(0, 4, clean_text(diag_curto), 0, 1)

    # Move cursor final para baixo do maior elemento (Radar tem aprox 45mm de altura)
    # y_ini + 50 garante que passe da altura da imagem e do texto
    pdf.set_y(max(pdf.get_y(), y_ini + 50)) 


# --- FUNÇÃO PRINCIPAL: CRIAÇÃO DO PDF INDIVIDUAL ---
def criar_pdf(atleta, res_finais, relatorio_dict, fig_radar, disclaimer):
    """Chamado pelo botão Individual do app.py"""
    pdf = PDFReport()
    pdf.set_margins(15, 15, 15)
    _desenhar_pagina_individual(pdf, atleta, res_finais, relatorio_dict, fig_radar, disclaimer)
    return pdf.output(dest='S').encode('latin-1', 'ignore')


# --- FUNÇÃO PRINCIPAL: CRIAÇÃO DO PDF DE GRUPO ---
def criar_relatorio_grupo(df_grupo, interpreter, disclaimer, nome_equipe="Time BioMS", logo_file=None):
    """Chamado pelo botão Grupo do app.py"""
    pdf = PDFReport()
    pdf.is_group = True
    pdf.nome_equipe = clean_text(nome_equipe)
    
    if "INTRA-GRUPO" in disclaimer.get('titulo', ''):
        pdf.info_referencia = f"Média do Grupo (N={len(df_grupo)})"
    else:
        pdf.info_referencia = "Banco de Elite Global"

    temp_logo = None
    if logo_file:
        # Pega a extensão do arquivo original (ex: .jpg)
        ext = os.path.splitext(logo_file.name)[1] if logo_file.name else ".png"
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
            tmp.write(logo_file.getvalue())
            temp_logo = tmp.name
        pdf.logo_custom_path = temp_logo

        
    pdf.set_margins(15, 15, 15)
    pdf.add_page() 

    # --- 1. Gráficos de Ranking (Estreitos + Descrição) ---
    metrics_info = [
        ('Z_BioMS_8', 'Ranking: Integridade Metabólica (BioMS-8)'),
        ('Z_BioMS_1', 'Ranking: Perfil Muscular (BioMS-1)'),
        ('Z_BioMS_5', 'Ranking: Explosão Muscular (BioMS-5)'),
        ('Z_BioMS_9', 'Ranking: Potencial de Velocidade (BioMS-9)')
    ]
    
    # Descrições para os gráficos
    descricoes = {
        'Z_BioMS_8': 'Integridade Metabólica: Capacidade de converter energia com o menor custo fisiológico.',
        'Z_BioMS_1': 'Perfil Muscular: Volume de massa magra do atleta.',
        'Z_BioMS_5': 'Explosão Muscular: Capacidade de explosão (saltos).',
        'Z_BioMS_9': 'Potencial de Velocidade: Prontidão neuromuscular (corrida).'
    }

    for metrica, titulo in metrics_info:
        # Imprime a descrição antes do gráfico
        texto_desc = descricoes.get(metrica, "")
        pdf.set_font('Arial', 'I', 9)
        pdf.set_text_color(100, 100, 100) # Cinza
        pdf.cell(0, 5, clean_text(texto_desc), 0, 1, 'L')
        
        # Gera gráfico
        fig = interpreter.plot_ranking_batch(df_grupo, metrica, titulo)
        fig.set_size_inches(8, 5) # Mais estreito
        
        path = None
        try:
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
                fig.savefig(tmp.name, dpi=90, bbox_inches='tight')
                path = tmp.name
            
            # Insere imagem
            pdf.image(path, x=10, w=190, h=85)
        except Exception as e:
            print(f"Erro ao inserir gráfico de ranking: {e}")
        finally:
            plt.close(fig)
            if path and os.path.exists(path):
                os.remove(path)
        
        pdf.ln(1)

    # --- 2. Relatórios Individuais (Compactos + Texto Lateral) ---
    pdf.add_page() 
    pdf.set_font('Arial', 'B', 14)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(0, 10, clean_text("Detalhamento Individual & Diagnóstico"), 0, 1, 'C')
    pdf.ln(5)

    for idx, row in df_grupo.iterrows():
        atleta = row.to_dict()
        res_finais = {f'Z_{k}': row.get(f'Z_{k}', 0) for k in ['BioMS_1','BioMS_5','BioMS_8','BioMS_9']}
        res_finais.update({f'P_{k}': row.get(f'P_{k}', 50) for k in ['BioMS_1','BioMS_5','BioMS_8','BioMS_9']})
        
        dict_txt = interpreter.gerar_relatorio_inteligente(res_finais)
        fig = interpreter.plot_radar_chart(res_finais)
        
        _desenhar_atleta_compacto(pdf, atleta, res_finais, dict_txt, fig)
        plt.close(fig)

    if temp_logo and os.path.exists(temp_logo):
        try: os.remove(temp_logo)
        except: pass

    return pdf.output(dest='S').encode('latin-1', 'ignore')

# --- FUNÇÃO NOVA: CRIAÇÃO DO PDF DO Z-SCORE UNIVERSAL ---
def criar_relatorio_zscore_universal(df_calc, nome_teste, fig_chart, logo_path=None):
    """Gera um PDF elegante contendo o gráfico customizado e a tabela de dados"""
    pdf = PDFReport()
    pdf.is_group = True
    pdf.nome_equipe = clean_text(f"Análise de Desempenho: {nome_teste}")
    pdf.info_referencia = "Média do Grupo"
    pdf.logo_custom_path = logo_path
    
    pdf.set_margins(15, 15, 15)
    pdf.add_page()
    
    # 1. Título Interno
    pdf.set_font('Arial', 'B', 14)
    pdf.set_text_color(44, 62, 80)
    pdf.cell(0, 10, clean_text(f"Ranking Z-Score: {nome_teste}"), 0, 1, 'C')
    pdf.ln(5)
    
    # 2. Inserir o Gráfico
    # 2. Inserir o Gráfico
    img_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            fig_chart.savefig(tmp.name, dpi=120, bbox_inches='tight')
            img_path = tmp.name
            
        pdf.image(img_path, x=10, w=190)
    except Exception as e:
        print(f"Erro no gráfico Z-Score Universal: {e}")
    finally:
        if img_path and os.path.exists(img_path):
            os.remove(img_path)
            
    pdf.ln(10)
    
    # 3. Tabela de Dados Exatos
    pdf.set_font('Arial', 'B', 10)
    pdf.set_fill_color(240, 240, 240)
    pdf.cell(80, 8, 'Nome do Atleta', 1, 0, 'C', fill=True)
    pdf.cell(50, 8, 'Valor Obtido', 1, 0, 'C', fill=True)
    pdf.cell(50, 8, 'Z-Score', 1, 1, 'C', fill=True)
    
    pdf.set_font('Arial', '', 10)
    for idx, row in df_calc.iterrows():
        pdf.cell(80, 8, clean_text(str(row['Nome do Atleta'])), 1, 0, 'L')
        pdf.cell(50, 8, f"{row['Valor do Teste']:.2f}", 1, 0, 'C')
        pdf.cell(50, 8, f"{row['Z_Score']:.2f}", 1, 1, 'C')

    return pdf.output(dest='S').encode('latin-1', 'ignore')

# --- FUNÇÃO NOVA: CRIAÇÃO DO PDF NORMATIVO LONGITUDINAL ---
def criar_relatorio_normativo_longitudinal(nome_aluno, idade, dados_exercicios, logo_path=None):
    """Gera um PDF contendo a evolução longitudinal de 1RM do aluno"""
    pdf = PDFReport()
    pdf.is_group = True # Usamos o layout de grupo porque ele tem aquele cabeçalho bonito
    pdf.nome_equipe = clean_text(f"Evolução Normativa: {nome_aluno} ({idade} anos)")
    pdf.info_referencia = "Comparativo: Literatura Científica"
    pdf.logo_custom_path = logo_path
    
    pdf.set_margins(15, 15, 15)
    pdf.add_page()
    
    pdf.set_y(55)

    # Título Principal Interno
    pdf.set_font('Arial', 'B', 14)
    pdf.set_text_color(44, 62, 80)
    pdf.cell(0, 8, clean_text("Relatório de Progresso e Força Máxima (1RM)"), 0, 1, 'C')
    
    # Adicionando o Nome do Aluno em destaque!
    pdf.set_font('Arial', '', 12)
    pdf.set_text_color(100, 100, 100) # Cinza elegante
    pdf.cell(0, 6, clean_text(f"Aluno(a): {nome_aluno} | Idade: {idade} anos"), 0, 1, 'C')
    pdf.ln(8)
    
    # Loop inteligente: vai imprimir um gráfico por exercício e pular página se precisar
    for item in dados_exercicios:
        exe = item['exercicio']
        fig = item['figura']
        evolucao = item['evolucao']
        
        # Se estiver muito perto do fim da página, cria uma nova
        if pdf.get_y() > 210:
            pdf.add_page()
            
        # Nome do Exercício
        pdf.set_font('Arial', 'B', 12)
        pdf.set_text_color(44, 62, 80)
        pdf.cell(0, 8, clean_text(f"Exercício: {exe}"), 0, 1, 'L')
        
        # Texto de Progresso (Verde para Positivo, Vermelho para Negativo)
        if evolucao:
            pdf.set_font('Arial', 'B', 10)
            if "+" in evolucao:
                pdf.set_text_color(39, 174, 96) # Verde
            else:
                pdf.set_text_color(192, 57, 43) # Vermelho
            pdf.cell(0, 6, clean_text(f"Progresso Estimado: {evolucao}"), 0, 1, 'L')
            
        # Inserir o Gráfico
       # Inserir o Gráfico
        img_path = None
        try:
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
                # Reajusta para caber bem na folha A4
                fig.set_size_inches(7, 2.6)
                fig.savefig(tmp.name, dpi=120, bbox_inches='tight')
                img_path = tmp.name
                
            pdf.image(img_path, x=30, w=150)
        except Exception as e:
            print(f"Erro no gráfico Normativo: {e}")
        finally:
            if img_path and os.path.exists(img_path):
                os.remove(img_path)
                
        pdf.ln(5) # Espaço antes do próximo exercício

    return pdf.output(dest='S').encode('latin-1', 'ignore')