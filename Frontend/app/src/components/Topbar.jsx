// Frontend/app/src/components/Topbar.jsx
import React, { useState, useEffect, useContext } from 'react';
import { useNavigate } from 'react-router-dom';
import authService from '../services/authService'; 
// Se você criar um AuthContext, importe-o:
// import { AuthContext } from '../contexts/AuthContext'; 

const handleLogout = (navigate, authContextSetter) => { 
  localStorage.removeItem('accessToken');
  // Limpar também o refresh token se estiver usando e armazenando-o
  // localStorage.removeItem('refreshToken'); 
  if (authContextSetter) {
    authContextSetter(null); 
  }
  navigate('/login');
};

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
  
  // const { currentUser, setCurrentUser } = useContext(AuthContext); // Exemplo com Contexto
  const [currentUser, setCurrentUser] = useState(null); 
  const [loadingUser, setLoadingUser] = useState(true);

  useEffect(() => {
    const fetchUserData = async () => {
      const token = localStorage.getItem('accessToken');
      console.log('Topbar useEffect: token from localStorage:', token); // DEBUG
      if (token) { 
        setLoadingUser(true);
        try {
          console.log('Topbar: Fetching user data...'); // DEBUG
          const user = await authService.getCurrentUser(); 
          console.log('Topbar: User data fetched:', user); // DEBUG
          if (user) {
            setCurrentUser(user);
          } else {
            console.log('Topbar: No user data returned from getCurrentUser, logging out.'); // DEBUG
            handleLogout(navigate, setCurrentUser); 
          }
        } catch (error) {
          console.error("Topbar: Erro ao buscar dados do usuário:", error.response || error.message || error); // DEBUG
          if (error.response && error.response.status === 401) {
            console.log('Topbar: 401 error on fetching user, logging out.'); // DEBUG
            handleLogout(navigate, setCurrentUser);
          }
          // Mesmo se não for 401, mas houver erro, talvez seja melhor deslogar
          // ou pelo menos limpar o estado currentUser.
          // setCurrentUser(null); // Limpa usuário em caso de outros erros
        } finally {
          setLoadingUser(false);
        }
      } else {
        console.log('Topbar: No token found, user not logged in or already logged out.'); // DEBUG
        setLoadingUser(false); 
        // Não é necessário redirecionar aqui, ProtectedRoute deve cuidar disso
      }
    };
    fetchUserData();
  }, [navigate]); 


  const userNameDisplay = loadingUser ? "Carregando..." : (currentUser?.nome_completo || currentUser?.email || "Usuário");
  const userInitials = loadingUser ? "..." : getInitials(currentUser?.nome_completo || currentUser?.email);

  return (
    <header className="topbar">
      <h1>{viewTitle || "Dashboard"}</h1>
      <div 
        className="user-area"
        tabIndex="0" 
        onMouseEnter={() => setUserMenuOpen(true)}
        onMouseLeave={() => setUserMenuOpen(false)}
        onClick={() => setUserMenuOpen(prev => !prev)}
        onFocus={() => setUserMenuOpen(true)} // Para acessibilidade com teclado
        onBlur={() => setTimeout(() => setUserMenuOpen(false), 150)} // Pequeno delay para permitir clique no menu
      >
        <div className="user-avatar">
          {userInitials}
        </div>
        <span className="user-name">{userNameDisplay}</span>
        
        {userMenuOpen && (
          <div className="user-menu" style={{ display: 'flex' }}> {/* Mantido flex para layout interno dos botões */}
            <button onClick={() => { setUserMenuOpen(false); navigate('/configuracoes'); }}> 
              <span style={{color:"#7c3aed",verticalAlign:"middle", marginRight:"5px"}}>&#9881;&#65039;</span> 
              Configurações
            </button>
            <button onClick={() => { setUserMenuOpen(false); handleLogout(navigate, setCurrentUser); }}>
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
