/**
 * Module landing page.
 *
 * Presents the public marketing surface for CatalogAI with product value,
 * pricing and conversion links into the authenticated app.
 */

import React from 'react';
import { Link } from 'react-router-dom';
import './LandingPage.css';

const features = [
  {
    icon: '🔍',
    title: 'Importação inteligente',
    desc: 'Suba catálogos PDF ou planilhas. A IA extrai produtos, preços e atributos automaticamente.',
  },
  {
    icon: '✨',
    title: 'Enriquecimento com IA',
    desc: 'Gere títulos, descrições e atributos otimizados para cada canal de venda com GPT-4o e Gemini.',
  },
  {
    icon: '📦',
    title: 'Gestão centralizada',
    desc: 'Organize produtos por fornecedor, tipo e status. Exporte tudo pronto para marketplaces.',
  },
];

const plans = [
  {
    name: 'Grátis',
    price: 'R$ 0',
    period: '/mês',
    features: ['50 produtos', '10 enriquecimentos/mês', '20 gerações de IA/mês'],
    cta: 'Começar grátis',
    href: '/signup',
    highlight: false,
  },
  {
    name: 'Pro',
    price: 'R$ 97',
    period: '/mês',
    features: [
      'Produtos ilimitados',
      '500 enriquecimentos/mês',
      '1.000 gerações de IA/mês',
      'Suporte prioritário',
    ],
    cta: 'Assinar Pro',
    href: '/signup?plano=pro',
    highlight: true,
  },
];

export default function LandingPage() {
  return (
    <div className="lp-root">
      <nav className="lp-nav">
        <span className="lp-logo">CatalogAI</span>
        <div className="lp-nav-links">
          <a href="#features">Funcionalidades</a>
          <a href="#pricing">Planos</a>
          <Link to="/login" className="lp-btn-outline">Entrar</Link>
          <Link to="/signup" className="lp-btn-primary">Criar conta</Link>
        </div>
      </nav>

      <section className="lp-hero">
        <div className="lp-hero-content">
          <h1>
            Seu catálogo de produtos,
            <br />
            <span className="lp-accent">enriquecido com IA</span>
          </h1>
          <p className="lp-hero-sub">
            Importe catálogos de fornecedores, gere descrições e títulos otimizados com GPT-4o e Gemini,
            e exporte tudo pronto para marketplaces em minutos.
          </p>
          <div className="lp-hero-ctas">
            <Link to="/signup" className="lp-btn-primary lp-btn-lg">Começar grátis</Link>
            <Link to="/login" className="lp-btn-outline lp-btn-lg">Já tenho conta</Link>
          </div>
        </div>
        <div className="lp-hero-visual">
          <div className="lp-mockup">
            <div className="lp-mockup-bar">
              <span />
              <span />
              <span />
            </div>
            <div className="lp-mockup-body">
              <div className="lp-mockup-row lp-mockup-header" />
              {[1, 2, 3, 4].map((item) => (
                <div key={item} className="lp-mockup-row">
                  <div className="lp-mockup-cell lp-cell-img" />
                  <div className="lp-mockup-cell lp-cell-wide" />
                  <div className="lp-mockup-cell lp-cell-mid" />
                  <div className="lp-mockup-cell lp-cell-badge" />
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      <section className="lp-section" id="features">
        <h2 className="lp-section-title">Tudo que você precisa</h2>
        <div className="lp-features">
          {features.map((feature) => (
            <div key={feature.title} className="lp-feature-card">
              <span className="lp-feature-icon">{feature.icon}</span>
              <h3>{feature.title}</h3>
              <p>{feature.desc}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="lp-section lp-section-dark" id="pricing">
        <h2 className="lp-section-title">Planos simples</h2>
        <div className="lp-plans">
          {plans.map((plan) => (
            <div key={plan.name} className={`lp-plan-card ${plan.highlight ? 'lp-plan-highlight' : ''}`}>
              {plan.highlight ? <span className="lp-plan-badge">Mais popular</span> : null}
              <h3>{plan.name}</h3>
              <div className="lp-plan-price">
                <strong>{plan.price}</strong>
                <span>{plan.period}</span>
              </div>
              <ul>
                {plan.features.map((feature) => (
                  <li key={feature}>
                    <span className="lp-check">✓</span> {feature}
                  </li>
                ))}
              </ul>
              <Link to={plan.href} className={plan.highlight ? 'lp-btn-primary' : 'lp-btn-outline'}>
                {plan.cta}
              </Link>
            </div>
          ))}
        </div>
      </section>

      <footer className="lp-footer">
        <span>© 2025 CatalogAI</span>
        <Link to="/login">Entrar</Link>
        <Link to="/signup">Criar conta</Link>
      </footer>
    </div>
  );
}
