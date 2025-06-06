// Frontend/app/src/pages/DashboardPage.jsx
import React, { useState, useEffect } from 'react';
import authService from '../services/authService'; // Mantido para getCurrentUser
import adminService from '../services/adminService'; // NOVO: Importar o adminService
import { showErrorToast } from '../utils/notifications';

// Os dados mockados restantes podem ser usados para as partes do dashboard que ainda não têm dados reais
const mockDashboardData = {
  productsByStatus: [
    { label: "Pendentes", value: 38, barWidth: "38%", barColor: "var(--warning)" },
    { label: "Enriquecidos", value: 54, barWidth: "54%", barColor: "var(--success)" },
    { label: "Completos", value: 8, barWidth: "8%", barColor: "var(--info)" }
  ],
  alerts: [
    { id: 1, messageHtml: "⚠️ <b>2 produto(s)</b> sem descrição" },
    { id: 2, messageHtml: "🔄 <b>2 produto(s)</b> pendente(s) de enriquecimento" }
  ],
  activityFeed: [
    { id: 1, icon: "📝", message: "3 títulos gerados por IA", date: "18/05/2025" },
    { id: 2, icon: "✅", message: "Produto MINI REFRIGERATOR enriquecido", date: "17/05/2025" },
    { id: 3, icon: "📦", message: "Planilha importada", date: "16/05/2025" }
  ],
  searchResults: [
    { id: 1, typeIcon: "📦", name: "MINI REFRIGERATOR 18L DREIHA CBX QUADRIVOLT", status: "Pendente", statusColor: "#d99a18" },
    { id: 2, typeIcon: "📦", name: "MINI COOLER 10L COMPACT", status: "Enriquecido", statusColor: "#39b664" },
    { id: 3, typeIcon: "🏢", name: "MiniDistribuidora", status: "Ativo", statusColor: "#39b664" },
  ]
};

function DashboardPage() {
  const [currentUser, setCurrentUser] = useState(null);
  const [adminStats, setAdminStats] = useState(null);
  const [loading, setLoading] = useState(true);
  // const [error, setError] = useState(null); // Erros serão tratados por toasts

  useEffect(() => {
    const fetchData = async () => {
      setLoading(true);
      try {
        const user = await authService.getCurrentUser();
        setCurrentUser(user);

        if (user && user.is_superuser) {
          // CORREÇÃO: Usar adminService para getTotalCounts
          const counts = await adminService.getTotalCounts();
          setAdminStats(counts);
        }
      } catch (err) {
        const errorMsg = err.message || err.detail || 'Falha ao carregar dados do dashboard.';
        showErrorToast(errorMsg);
        console.error("Erro ao carregar dados do dashboard:", err);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, []);

  const formattedStats = adminStats ? [
    {
      value: adminStats.total_produtos?.toString() || "0",
      label: "Total Produtos",
      // MODIFICADO: Usando total_usuarios de adminStats se disponível
      comparison: `Usuários: ${adminStats.total_usuarios || adminStats.total_users || 0}`, 
      barWidth: "75%",
      barColor: "var(--success)",
      barGradient: "linear-gradient(90deg,var(--success),#e8faed 85%)",
      icon: "📦"
    },
    {
      value: adminStats.total_fornecedores?.toString() || "0",
      label: "Total Fornecedores",
      comparison: `Gerações IA (mês): ${adminStats.total_geracoes_ia_mes || 0}`, // Usando outro stat aqui
      barWidth: "60%",
      barColor: "var(--warning)",
      barGradient: "linear-gradient(90deg,var(--warning),#fff4d5 85%)",
      icon: "🏢"
    },
    {
      value: adminStats.total_usos_ia?.toString() || // Se o backend retornar total_usos_ia
                 adminStats.total_geracoes_ia_mes?.toString() || "0", // Fallback para total_geracoes_ia_mes
      label: "Total Usos IA (mês)", // Rótulo mais específico
      comparison: `Enriquecimentos (mês): ${adminStats.total_enriquecimentos_mes || 0}`,
      barWidth: "80%",
      barColor: "var(--info)",
      barGradient: "linear-gradient(90deg,var(--info),#eef6fa 85%)",
      icon: "🤖"
    },
    {
      value: adminStats.total_usuarios?.toString() || adminStats.total_users?.toString() || "0",
      label: "Total Usuários",
      comparison: "",
      barWidth: "50%",
      barColor: "var(--primary)",
      barGradient: "linear-gradient(90deg,var(--primary),#e8ebff 85%)",
      icon: "👥"
    }
  ] : [];

  const data = mockDashboardData; 

  if (loading) {
    return <p style={{padding: "20px"}}>Carregando dashboard...</p>;
  }

  return (
    <div id="dashboard-pro-main">
      {currentUser && currentUser.is_superuser && adminStats && (
        <div className="pro-stats-row">
          {formattedStats.map((stat, index) => (
            <div className="pro-card-metric" key={index} style={{ '--bar-color': stat.barColor }}>
              <div className="pro-metric-bar-bg">
                <div className="pro-metric-bar" style={{ width: stat.barWidth, background: stat.barGradient }}></div>
              </div>
              <div className="pro-metric-icon">{stat.icon}</div>
              <span className="pro-metric-value">{stat.value}</span>
              <span className="pro-metric-label">{stat.label}</span>
              <span className="pro-metric-comp">{stat.comparison}</span>
            </div>
          ))}
        </div>
      )}

      {(!currentUser || !currentUser.is_superuser) && !loading && (
        <div style={{ padding: '20px', textAlign: 'center' }}>
          <h2>Bem-vindo ao TDAI!</h2>
          <p>Seu dashboard personalizado será implementado aqui em breve.</p>
        </div>
      )}

      {currentUser && currentUser.is_superuser && (
        <div className="dashboard-flex-row">
          <div className="dashboard-col dashboard-col-esq">
            <div className="pro-bar-chart">
              <div className="pro-bar-title">Produtos por Status (Mock)</div>
              {data.productsByStatus.map((item, index) => (
                <div className="pro-bar-row" key={index}>
                  <span className="pro-bar-label">{item.label}</span>
                  <div className="pro-bar-bg">
                    <div className="pro-bar" style={{ width: item.barWidth, background: item.barColor }}></div>
                  </div>
                  <span className="pro-bar-value">{item.value}</span>
                </div>
              ))}
            </div>
            <div className="pro-alert-card">
              <div className="pro-alert-title">Pendências (Mock)</div>
              <div className="pro-alert-list">
                {data.alerts.map(alert => (
                  <div key={alert.id} dangerouslySetInnerHTML={{ __html: alert.messageHtml }} />
                ))}
              </div>
            </div>
            <div className="pro-feed-card">
              <div className="pro-feed-title">Últimas Atividades (Mock)</div>
              <ul className="pro-feed-list">
                {data.activityFeed.map(item => (
                  <li className="pro-feed-item" key={item.id}>
                    <span className="pro-feed-ico">{item.icon}</span>
                    <span className="pro-feed-msg">{item.message}</span>
                    <span className="pro-feed-date">{item.date}</span>
                  </li>
                ))}
              </ul>
            </div>
          </div>
          <div className="dashboard-col dashboard-col-dir">
            <div className="pro-search-bar">
              <span className="pro-search-ico">🔎</span>
              <input type="text" defaultValue="MINI (Mock)" readOnly />
            </div>
            <div className="search-results-table table-scroll-box">
              <table>
                <thead>
                  <tr>
                    <th style={{ textAlign: 'left' }}>Tipo</th>
                    <th style={{ textAlign: 'left' }}>Nome</th>
                    <th style={{ textAlign: 'left' }}>Status</th>
                    <th style={{ textAlign: 'right' }}>Ação</th>
                  </tr>
                </thead>
                <tbody>
                  {data.searchResults.map(item => (
                    <tr key={item.id}>
                      <td><span title={item.typeIcon === "📦" ? "Produto" : "Fornecedor"}>{item.typeIcon}</span></td>
                      <td style={{ fontWeight: 600 }}>{item.name}</td>
                      <td><span style={{ color: item.statusColor, fontWeight: 500 }}>{item.status}</span></td>
                      <td style={{ textAlign: 'right' }}>
                        <button className="btn-detalhe">Ver Detalhes</button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default DashboardPage;
