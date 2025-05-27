import React from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
// Se você criar um Sidebar.css específico, importe-o aqui:
// import './Sidebar.css'; 

// Função para simular logout (substitua pela sua lógica real depois)
// Por exemplo, chamando uma função do seu authService.js
const handleLogout = (navigate) => {
  localStorage.removeItem('accessToken'); // Limpa o token
  // Adicione aqui qualquer outra lógica de limpeza de estado de usuário
  alert('Logout realizado com sucesso! (Simulado)');
  navigate('/login'); // Redireciona para a página de login
};

function Sidebar() {
  const navigate = useNavigate();

  // As classes CSS (sidebar, logo, nav, active, logout) vêm do seu CSS global
  // que você configurou no index.css baseado no allinone.html
  return (
    <aside className="sidebar">
      <div className="logo">TDAi</div>
      <nav>
        <NavLink 
          to="/dashboard" 
          className={({ isActive }) => isActive ? "active" : ""}
        >
          Dashboard
        </NavLink>
        <NavLink 
          to="/produtos" 
          className={({ isActive }) => isActive ? "active" : ""}
        >
          Produtos
        </NavLink>
        <NavLink 
          to="/fornecedores" 
          className={({ isActive }) => isActive ? "active" : ""}
        >
          Fornecedores
        </NavLink>
        <NavLink 
          to="/enriquecimento" 
          className={({ isActive }) => isActive ? "active" : ""}
        >
          Enriquecimento
        </NavLink>
        <NavLink 
          to="/historico" 
          className={({ isActive }) => isActive ? "active" : ""}
        >
          Histórico
        </NavLink>
        <NavLink 
          to="/plano" 
          className={({ isActive }) => isActive ? "active" : ""}
        >
          Meu Plano
        </NavLink>
        <NavLink 
          to="/configuracoes" 
          className={({ isActive }) => isActive ? "active" : ""}
        >
          Configurações
        </NavLink>
      </nav>
      <div className="logout" onClick={() => handleLogout(navigate)}>
        Sair
      </div>
    </aside>
  );
}

export default Sidebar;