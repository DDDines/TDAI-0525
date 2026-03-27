import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import LoadingPopup from '../LoadingPopup.jsx';

describe('LoadingPopup', () => {
  test('renders popup when open with logo, title and message', () => {
    render(
      <LoadingPopup
        isOpen={true}
        title="Importando"
        message="Loading test"
      />
    );

    expect(screen.getByAltText('CommerceFolio')).toBeInTheDocument();
    expect(screen.getByText('Importando')).toBeInTheDocument();
    expect(screen.getByText('Loading test')).toBeInTheDocument();
  });

  test('uses defaults when optional props are omitted', () => {
    render(<LoadingPopup isOpen={true} />);

    expect(screen.getByText('Processando')).toBeInTheDocument();
    expect(screen.getByText('Aguarde...')).toBeInTheDocument();
  });

  test('renders nothing when the popup is closed', () => {
    const { container } = render(<LoadingPopup isOpen={false} message="Hidden" />);

    expect(container).toBeEmptyDOMElement();
  });
});
