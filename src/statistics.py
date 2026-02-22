import numpy as np
import pandas as pd
from scipy import stats

class BioMSStatistics:
    def __init__(self, df_ref):
        # Recebe a base de referência.
        # Pode ser o Banco de Dados Global (Camada 1) OU o DataFrame do Grupo (Camada 2).
        self.df_ref = df_ref.copy()
        
    def compare_athlete(self, atleta_metrics):
        resultados = {}

        # 1. Identificar o Grupo de Comparação (Filtro por Sexo)
        try:
            sexo_atleta = int(atleta_metrics.get('SEXO', 0))
            
            # Filtro robusto para garantir tipos compatíveis
            if 'SEXO' in self.df_ref.columns:
                col_sexo_db = pd.to_numeric(self.df_ref['SEXO'], errors='coerce').fillna(0).astype(int)
                df_grupo = self.df_ref[col_sexo_db == sexo_atleta].copy()
            else:
                # Se não houver coluna sexo, usa a base toda
                df_grupo = self.df_ref.copy()
            
        except Exception as e:
            # Em caso de erro, usa a base completa fornecida
            df_grupo = self.df_ref.copy()

        # [AJUSTE FUNDAMENTAL PARA GRUPOS/TIMES]
        # Reduzimos o fallback de 10 para 3. 
        # Motivo: Em análises intra-grupo (times), é comum ter poucos atletas (ex: 5 titulares).
        # Se for < 3, o desvio padrão não é confiável, então aí sim usamos o 'df_ref' (grupo todo misto) como fallback.
        if df_grupo.empty or len(df_grupo) < 3:
            df_grupo = self.df_ref.copy()

        # 2. Cálculos Estatísticos (Z-Score e Percentil)
        metricas = ['BioMS_1', 'BioMS_5', 'BioMS_8', 'BioMS_9']
        
        for col in metricas:
            val = atleta_metrics.get(col)
            
            # Só calcula se o valor do atleta existe e a coluna existe no banco/grupo
            if val is not None and col in df_grupo.columns:
                
                # LIMPEZA ESTATÍSTICA CRÍTICA:
                # 1. Converte para numérico
                # 2. Substitui Infinitos por NaN
                # 3. Remove NaNs
                dados = pd.to_numeric(df_grupo[col], errors='coerce') \
                          .replace([np.inf, -np.inf], np.nan) \
                          .dropna()
                
                # Só prossegue se sobrar dados válidos após a limpeza
                if not dados.empty:
                    mu = dados.mean()
                    sigma = dados.std(ddof=1)
                    
                    # Evita divisão por zero no Z-Score se todos os valores forem iguais (sigma=0)
                    if sigma > 1e-6:
                        z_score = (val - mu) / sigma
                        percentil = stats.percentileofscore(dados, val)
                    else:
                        # Se não há variação no grupo (todos iguais), o score é neutro (0)
                        z_score = 0
                        percentil = 50
                    
                    resultados[f'Z_{col}'] = z_score
                    resultados[f'P_{col}'] = percentil
                else:
                    resultados[f'Z_{col}'] = 0
                    resultados[f'P_{col}'] = 50
            else:
                resultados[f'Z_{col}'] = 0
                resultados[f'P_{col}'] = 50

        # 3. Classificação por Quadrante
        z1 = resultados.get('Z_BioMS_1', 0)
        z9 = resultados.get('Z_BioMS_9', 0)
        resultados['Classificacao'] = self._definir_quadrante(z1, z9)
        
        return resultados

    def _definir_quadrante(self, z_struct, z_power):
        """
        Cruzamento de BioMS-1 (Estrutura/Massa) com BioMS-5 (Potência/Qualidade).
        """
        if z_struct is None or z_power is None: return "Indefinido"
        
        cut = 0.2
        
        if z_struct >= cut and z_power >= cut:
            return "💎 Atleta Híbrido (Elite)" 
        elif z_struct >= cut and z_power < cut:
            return "🚜 Trator (Força Pura)" 
        elif z_struct < cut and z_power >= cut:
            return "⚡ Velocista (Motor Leve)" 
        elif z_struct < -0.5 and z_power < -0.5:
            return "🚑 Destreinado/Risco" 
        else:
            return "⚖️ Balanceado (Em Desenvolvimento)"