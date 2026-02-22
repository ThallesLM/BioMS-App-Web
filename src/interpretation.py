import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

class BioMSInterpreter:
    """
    Classe responsável pela tradução dos dados numéricos (BioMS Scores) 
    em narrativa de Engenharia de Performance Humana.
    """
    
    def __init__(self):
        plt.style.use('bmh')
        
        # --- KNOWLEDGE BASE: Engenharia de Performance (Perspectiva de Elite) ---
        self.knowledge_base = {
            'BioMS_1': { 
                'titulo': 'Perfil Muscular',
                'conceito': 'Mede a reserva estrutural (volume e densidade muscular). A referência (Z=0) é o teto de atletas federados.',
                'elite':    ('Reserva de Elite', 'Estrutura superdesenvolvida. Seu volume muscular é comparável ao teto fisiológico de atletas de alto rendimento. Excelente blindagem articular e potencial de força bruta.'),
                'alto':     ('Alta Densidade', 'Chassi robusto, bem acima da média populacional. Possui estrutura mais que suficiente para suportar altos volumes de treinamento intenso com segurança.'),
                'normal':   ('Estrutura Funcional', 'Volume muscular adequado para a vida ativa. Distante da hipertrofia de um atleta, mas perfeitamente funcional para saúde, demandas diárias e treinos regulares.'),
                'alerta':   ('Volume Moderado', 'Sua reserva de massa magra está abaixo do referencial atlético. Focar em treinamento de força (hipertrofia) ajudará a proteger as articulações no longo prazo.'),
                'critico':  ('Distante do Teto Atlítico', 'Perfil com baixa reserva de massa magra em relação à elite. Recomenda-se forte prioridade em ganho estrutural para melhorar a autonomia, metabolismo e longevidade.')
            },
            'BioMS_5': { 
                'titulo': 'Potência Muscular',
                'conceito': 'Capacidade de gerar força rápida e explosão (RFD). A referência (Z=0) são atletas de esportes de potência.',
                'elite':    ('Potência Explosiva (Nível Elite)', 'Seu sistema neuromuscular opera com a mesma eficiência, taxa de disparo e explosão de saltadores ou velocistas profissionais.'),
                'alto':     ('Alta Reatividade', 'Músculos potentes e reativos. Ótima capacidade de converter força em movimento rápido, conferindo vantagem em práticas esportivas dinâmicas.'),
                'normal':   ('Capacidade Padrão (Não-Atleta)', 'Resposta contrátil dentro do esperado para a população geral. O músculo tem força, mas não possui o "arranque" e a explosão característicos de esportistas de elite.'),
                'alerta':   ('Baixa Explosão', 'Predominância de fibras de contração lenta ou letargia neural. Atividades de aceleração rápida serão mais difíceis, indicando necessidade de treinos de potência.'),
                'critico':  ('Resposta Contrátil Lenta', 'Distância significativa da eficiência de explosão atlética. O sistema absorve impactos de forma lenta; a inclusão gradual de estímulos neuromusculares é recomendada.')
            },
            'BioMS_8': { 
                'titulo': 'Integridade Metabólica',
                'conceito': 'Eficiência celular na conversão de energia, inversamente proporcional ao ruído inflamatório. O nível Elite exige um "motor" extremamente limpo.',
                'elite':    ('Homeostase Ótima', 'Ambiente celular altamente otimizado, sem fricção metabólica. Seu corpo produz e utiliza energia com o mesmo custo baixíssimo de um atleta de elite.'),
                'alto':     ('Ambiente Celular Preservado', 'Excelente eficiência. Baixíssima probabilidade de resistência metabólica, indicando uma recuperação rápida e processamento energético fluído.'),
                'normal':   ('Metabolismo Funcional', 'Processamento energético adequado. Lida bem com o dia a dia, mas sem a eficiência extrema (baixo custo fisiológico) exigida na alta performance.'),
                'alerta':   ('Fricção Metabólica Inicial', 'Sinais de que o corpo gasta um pouco mais de energia para manter funções básicas. Pode indicar estresse acumulado ou necessidade de ajustes na recuperação/nutrição.'),
                'critico':  ('Baixa Eficiência Sistêmica', 'O metabolismo está trabalhando com alto custo e possível ruído inflamatório. Distante da "limpeza" atlética, dificultando a recuperação e a queima eficiente de gordura.')
            },
            'BioMS_9': { 
                'titulo': 'Prontidão Neuromuscular',
                'conceito': 'Qualidade da membrana celular combinada à condução nervosa para resistir à fadiga rápida. Comparativo com sprinters.',
                'elite':    ('Prontidão Neural Máxima', 'Sinalização elétrica nervo-músculo de altíssimo nível. Resiliência à fadiga e tempo de reação comparáveis a atletas de explosão.'),
                'alto':     ('Alta Resiliência', 'Membranas íntegras e rápida condução nervosa. O sistema suporta bem a intensidade e se recupera rapidamente entre os estímulos.'),
                'normal':   ('Prontidão Operacional', 'Comunicação nervosa adequada. Longe da reatividade extrema de um competidor, mas plenamente capaz de suportar a rotina de exercícios.'),
                'alerta':   ('Fadiga Precoce', 'A qualidade de condução do sinal pode estar reduzida. Indica que o sistema perde eficiência rapidamente sob estresse continuado.'),
                'critico':  ('Sinalização Lenta', 'Distância considerável da prontidão atlética. Sugere desgaste nas membranas ou letargia do sistema nervoso, necessitando foco em recuperação e modulação de treinos.')
            }
        }

    def get_context_disclaimer(self):
        return {
            "titulo": "Entendendo seus Resultados: A Perspectiva BioMS",
            "texto": (
                "Nossa tecnologia não busca diagnosticar doenças, mas sim medir a distância entre a sua condição atual "
                "e o **teto fisiológico da espécie humana** (atletas de elite federados).\n\n"
                "Resultados classificados como 'Padrão' ou 'Funcional' não indicam fraqueza, mas representam "
                "o comportamento normal de quem não vive do esporte. O BioMS é a sua bússola de longo prazo "
                "para construir um corpo mais resiliente, forte e eficiente, utilizando o esporte de alto rendimento como horizonte de evolução."
            )
        }


    def _classificar_z_score(self, z):
        if z >= 1.5: return 'elite', "#00fa21"   # Verde Elite
        elif z > 0.5: return 'alto', '#37e5f1'    # Verde Claro
        elif z >= -0.5: return 'normal', '#34495e' # Azul Neutro
        elif z > -1.5: return 'alerta', '#f39c12'  # Laranja
        else: return 'critico', '#e74c3c'          # Vermelho Suave

    def gerar_relatorio_inteligente(self, resultados):
        mapa_analise = {
            'BioMS_1': resultados.get('Z_BioMS_1', 0),
            'BioMS_5': resultados.get('Z_BioMS_5', 0),
            'BioMS_8': resultados.get('Z_BioMS_8', 0),
            'BioMS_9': resultados.get('Z_BioMS_9', 0),
        }

        relatorio_final = {}
        for chave, z_val in mapa_analise.items():
            classe, cor = self._classificar_z_score(z_val)
            kb_item = self.knowledge_base[chave]
            
            titulo_card, texto_desc = kb_item[classe]
            
            relatorio_final[chave] = {
                'titulo_card': titulo_card,
                'subtitulo': kb_item['conceito'],
                'texto': texto_desc,
                'classe': classe,
                'cor': cor,
                'score_z': z_val
            }
        return relatorio_final

    def plot_radar_chart(self, resultados_finais):
        labels = ['(Estrutura)', '(Potência)', '(Velocidade)', '(Integridade)']
        keys = ['Z_BioMS_1', 'Z_BioMS_5', 'Z_BioMS_9', 'Z_BioMS_8']
        
        values = [float(resultados_finais.get(k, 0)) for k in keys]
        values += values[:1]
        
        angles = np.linspace(0, 2 * np.pi, len(labels), endpoint=False).tolist()
        angles += angles[:1]

        # Reduzimos um pouco o tamanho para não ficar gigante na tela
        fig, ax = plt.subplots(figsize=(6, 6), subplot_kw=dict(polar=True))
        
        # Média Global: Fundo cinza super claro e linha pontilhada sutil
        ax.fill(angles, [0]*len(angles), color="#e2e8f0", alpha=0.5, label='Média Global')
        ax.plot(angles, [0]*len(angles), color="#94a3b8", linestyle='--', linewidth=1.2, alpha=0.8)

        # Performance do Atleta: Azul premium da marca, translúcido
        ax.plot(angles, values, color="#2980b9", linewidth=2.5, label='Sua Performance')
        ax.fill(angles, values, color="#3498db", alpha=0.2)
        
        ax.set_ylim(-2.5, 2.5)
        ax.set_yticks([-1.5, 0, 1.5])
        ax.set_yticklabels([]) # Remove os números dos anéis para limpar o design
        
        ax.set_xticks(angles[:-1])
        # UX Tip: Fonte menor (10), sem negrito, cor chumbo elegante
        ax.set_xticklabels(labels, fontsize=10, weight='normal', color="#4a5568")
        
        # Legenda flutuante (frameon=False remove a borda dura da caixinha)
        plt.legend(loc='upper right', bbox_to_anchor=(1.3, 1.1), fontsize=9, frameon=False)
        #plt.title("Matriz BioMS", pad=20, fontsize=14, fontweight='bold', color='#2c3e50')
        
        return fig
    
    def plot_gauge_performance(self, valor_z, titulo):
        fig, ax = plt.subplots(figsize=(8, 1.2))
        
        # UX Tip: Paleta "Médica" (tons pastéis relaxantes em vez de neon)
        cores = ['#fca5a5', '#fcd34d', '#e2e8f0', '#93c5fd', '#86efac']
        limites = [-3, -1.5, -0.5, 0.5, 1.5, 3]
        
        # UX Tip: Barra mais fina (height=0.35) para parecer um painel sofisticado
        for i in range(len(cores)):
            ax.barh(0, limites[i+1]-limites[i], left=limites[i], color=cores[i], alpha=0.8, height=0.35)
        
        val_plot = np.clip(valor_z, -2.9, 2.9)
        # Marcador mais elegante
        ax.axvline(val_plot, color='#2c3e50', linewidth=2, ymin=0.2, ymax=0.8)
        ax.scatter(val_plot, 0, color='#2c3e50', s=60, zorder=5)
        
        ax.set_xlim(-3, 3)
        ax.set_yticks([])
        ax.set_xticks([-2.25, 0, 2.25])
        # Textos com cinza médio (#64748b)
        ax.set_xticklabels(['Zona de\nDesenvolvimento', 'Média\nAtlética', 'Alta\nPerformance'], fontsize=9, color='#64748b')
        
        ax.set_title(titulo, fontsize=11, fontweight='bold', loc='left', color='#2c3e50')
        for spine in ax.spines.values(): spine.set_visible(False)
        
        # UX Tip: Aumenta o espaço em branco na base para as letras "respirarem"
        plt.subplots_adjust(bottom=0.45, top=0.85)
        return fig
    
    # --- NOVA FUNÇÃO ADICIONADA: RANKING DE GRUPO ---
    # No arquivo src/interpretation.py, garanta que esta função esteja assim:

    def plot_ranking_batch(self, df_grupo, metrica_z, titulo, cor_positiva="#69FF89", cor_negativa="#bc88ff", logo_path=None):
        """
        Gera um gráfico de colunas verticais (Ranking) personalizável e sem linhas de grade.
        """
        import matplotlib.pyplot as plt
        from PIL import Image
        from matplotlib.offsetbox import OffsetImage, AnnotationBbox

        # 1. Preparação e Limpeza
        col_label = 'Label' if 'Label' in df_grupo.columns else 'ID'
        df_plot = df_grupo.dropna(subset=[metrica_z]).copy()
        
        df_plot[col_label] = df_plot[col_label].fillna("Sem ID").astype(str)
        df_plot = df_plot.sort_values(by=metrica_z, ascending=False)

        # 2. Configuração do Canvas
        largura = max(10, len(df_plot) * 0.6)
        fig, ax = plt.subplots(figsize=(largura, 6.5))
        fig.patch.set_facecolor("#ffffff") 
        ax.set_facecolor('#ffffff')

        # 3. Barras (Usando as cores escolhidas pelo usuário)
        x_pos = range(len(df_plot))
        valores = df_plot[metrica_z]
        nomes = df_plot[col_label]
        
        cores_dinamicas = [cor_positiva if val >= 0 else cor_negativa for val in valores]
        bars = ax.bar(x_pos, valores, color=cores_dinamicas, edgecolor='none', width=0.65, zorder=3)

        # 4. Eixo X
        ax.set_xticks(x_pos)
        ax.set_xticklabels(nomes, rotation=45, ha='right', fontsize=10, weight='normal', color='#4a5568')
        
        ax.spines['bottom'].set_color('#cbd5e1')
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['left'].set_visible(False)

        # 5. Linhas de Referência (Discretas)
        ax.axhline(0, color='#94a3b8', linestyle='-', linewidth=1, zorder=2) 
        ax.axhline(1, color='#cbd5e1', linestyle='--', linewidth=1, zorder=2) 
        ax.axhline(-1, color='#cbd5e1', linestyle='--', linewidth=1, zorder=2) 

        # 6. Rótulos de Valores nas Barras
        for bar in bars:
            height = bar.get_height()
            offset = 0.08 if height >= 0 else -0.25
            va_align = 'bottom' if height >= 0 else 'top'
            
            ax.text(bar.get_x() + bar.get_width()/2, height + offset, 
                    f'{height:.2f}', 
                    ha='center', va=va_align, 
                    fontsize=9, weight='normal', color='#2c3e50')

        # 7. Inserção da Logo Customizada no Gráfico (Canto Superior Direito)
        if logo_path:
            try:
                img = Image.open(logo_path)
                import numpy as np
                img_array = np.array(img)
                imagebox = OffsetImage(img_array, zoom=0.12) # Zoom para não ficar gigante
                ab = AnnotationBbox(imagebox, (0.98, 0.95), xycoords='axes fraction', frameon=False, box_alignment=(1,1))
                ax.add_artist(ab)
            except Exception as e:
                pass # Se a imagem falhar, apenas segue sem quebrar o gráfico

        # 8. Acabamento (SEM GRADES)
        ax.set_title(titulo, fontsize=14, weight='normal', loc='left', color='#2c3e50', pad=20)
        ax.set_ylabel("Z-Score", fontsize=10, color='#64748b')
        ax.tick_params(axis='y', colors='#64748b', length=0)
        
        ymax = max(valores.max(), 1.5) + 0.5
        ymin = min(valores.min(), -1.5) - 0.5
        ax.set_ylim(ymin, ymax)
        
        # GRADE REMOVIDA: A linha abaixo foi apagada para deixar o fundo 100% limpo!
        ax.grid(False) 
        
        plt.subplots_adjust(bottom=0.25, top=0.90, left=0.08, right=0.98)
        
        return fig
    


    def plot_longitudinal_evolution(self, df_coletas, media_grupo, nome_exercicio, cor_aluno="#8b5cf6", logo_path=None):
            """
            Gera um gráfico de barras verticais comparando a média normativa 
            com as múltiplas coletas do aluno ao longo do tempo.
            """
            import matplotlib.pyplot as plt
            from PIL import Image
            from matplotlib.offsetbox import OffsetImage, AnnotationBbox

            # 1. Preparação dos dados para o gráfico
            # A primeira coluna é forçada a ser a "Média do Grupo"
            datas = ['Média da Idade'] + df_coletas['Data'].tolist()
            valores = [media_grupo] + df_coletas['Valor_Final'].tolist()
            
            # A primeira barra é cinza, as outras são da cor escolhida pelo usuário
            cores = ['#cbd5e1'] + [cor_aluno] * len(df_coletas) 

            # 2. Configuração do Canvas (Fundo Branco Premium)
            # A largura cresce automaticamente se tiverem muitas coletas!
            largura = max(6, len(datas) * 1.2) 
            fig, ax = plt.subplots(figsize=(largura, 3.5))
            fig.patch.set_facecolor('#ffffff')
            ax.set_facecolor('#ffffff')

            # 3. Desenhar as Barras Verticais
            x_pos = range(len(datas))
            bars = ax.bar(x_pos, valores, color=cores, edgecolor='none', width=0.4, zorder=3)

            # 4. A Linha Tracejada da Média
            # Ela nasce na altura exata da média e cruza para a direita
            ax.axhline(media_grupo, color='#94a3b8', linestyle='--', linewidth=1.5, zorder=2)

            # 5. Rótulos no eixo X (As datas)
            ax.set_xticks(x_pos)
            ax.set_xticklabels(datas, fontsize=10, weight='normal', color='#4a5568')

            # 6. Colocar o número flutuando em cima de cada barra
            for bar in bars:
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2, height + (max(valores)*0.03), 
                        f'{height:.1f}', 
                        ha='center', va='bottom', 
                        fontsize=10, weight='bold', color='#2c3e50')

            # 7. Limpeza Visual (Tirar grades e eixos desnecessários)
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)
            ax.spines['left'].set_visible(False)
            ax.spines['bottom'].set_color('#cbd5e1')
            ax.tick_params(axis='y', left=False, labelleft=False) # Esconde os números laterais para ficar mais limpo

            
            
            # Dá um respiro no teto do gráfico para o número não cortar
            ax.set_ylim(0, max(valores) * 1.25)
            
            ax.set_xlim(-0.75, max(len(datas), 4) - 0.25)

            plt.tight_layout()
            
            return fig