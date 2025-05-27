// Frontend/app/src/components/Topbar.jsx
import React, { useState, useEffect } from 'react';
import { useNavigate }
from 'react-router-dom';
// import authService from '../services/authService'; // Descomente quando tiver o serviço de auth para buscar dados do user

// Função para simular logout (similar à da Sidebar)
const handleLogout = (navigate) => {
  localStorage.removeItem('accessToken');
  // Limpe aqui qualquer outro estado global do usuário, se houver
  // Ex: userService.clearCurrentUser(); 
  navigate('/login');
};

// Função simples para obter iniciais de um nome
const getInitials = (name) => {
  if (!name || typeof name !== 'string') return '??';
  const names = name.split(' ');
  let initials = names[0].substring(0, 1).toUpperCase();
  if (names.length > 1) {
    initials += names[names.length - 1].substring(0, 1).toUpperCase();
  }
  return initials;
};

function Topbar({ viewTitle }) {
  const navigate = useNavigate();
  const [userMenuOpen, setUserMenuOpen] = useState(false);
  
  // TODO: Buscar e armazenar dados do usuário de forma mais robusta (ex: Context API ou Redux)
  // Por enquanto, vamos usar um nome de exemplo.
  // Você pode tentar buscar do localStorage se salvou algo lá após o login.
  const [currentUser, setCurrentUser] = useState({
    nome: "Usuário Exemplo", // Placeholder
    // email: "usuario@example.com"
  });

  // useEffect(() => {
  //   // Exemplo de como você poderia buscar dados do usuário ao montar o Topbar
  //   const fetchUserData = async () => {
  //     try {
  //       // const user = await authService.getCurrentUser(); // Supondo uma função no seu authService
  //       // if (user) {
  //       //   setCurrentUser(user);
  //       // } else {
  //       //   // Se não conseguir buscar o usuário, talvez redirecionar para login
  //       //   handleLogout(navigate);
  //       // }
  //     } catch (error) {
  //       console.error("Erro ao buscar dados do usuário:", error);
  //       // handleLogout(navigate); // Deslogar em caso de erro
  //     }
  //   };
  //   // fetchUserData();
  // }, [navigate]);


  const userNameDisplay = currentUser?.nome || "Usuário";
  const userInitials = getInitials(currentUser?.nome);

  return (
    <header className="topbar"> {/* Classe do allinone.html */}
      <h1>{viewTitle || "Dashboard"}</h1>
      <div 
        className="user-area"  /* Classe do allinone.html */
        tabIndex="0" 
        onMouseEnter={() => setUserMenuOpen(true)}
        onMouseLeave={() => setUserMenuOpen(false)}
        onClick={() => setUserMenuOpen(prev => !prev)} // Para toque/clique
      >
        <div className="user-avatar"> {/* Classe do allinone.html */}
          {userInitials}
        </div>
        <span className="user-name">{userNameDisplay}</span> {/* Classe do allinone.html */}
        
        {userMenuOpen && (
          <div className="user-menu" style={{ display: 'flex' }}> {/* Classe e estilo do allinone.html */}
            <button disabled>
              <span style={{color:"#7c3aed",verticalAlign:"middle", marginRight:"5px"}}>&#128100;</span> 
              Meu Perfil
            </button>
            <button disabled>
              <span style={{color:"#a3a3a3",verticalAlign:"middle", marginRight:"5px"}}>&#9881;&#65039;</span> 
              Configurações
            </button>
            <button onClick={() => handleLogout(navigate)}>
              <span style={{color:"var(--danger)",verticalAlign:"middle", marginRight:"5px"}}>➔</span> 
              Sair
            </button>
          </div>
        )}
      </div>
    </header>
  );
}

export default Topbar;