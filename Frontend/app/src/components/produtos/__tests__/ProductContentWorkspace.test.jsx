import React from 'react';
import { fireEvent, render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import ProductContentWorkspace from '../ProductContentWorkspace.jsx';

describe('ProductContentWorkspace', () => {
  test('renderiza os textos padrao com acentuacao correta', () => {
    render(<ProductContentWorkspace />);

    expect(screen.getByRole('heading', { name: '5 títulos sugeridos' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Descrição completa' })).toBeInTheDocument();
    expect(screen.getAllByText('Título ainda não gerado para esta posição.')).toHaveLength(5);
    expect(screen.getByText('Descrição ainda não gerada.')).toBeInTheDocument();
  });

  test('permite editar titulos e descricao no modo editavel', () => {
    const handleTitleChange = jest.fn();
    const handleDescriptionChange = jest.fn();

    render(
      <ProductContentWorkspace
        editable
        titles={['Título inicial']}
        description="Descrição inicial"
        onTitleChange={handleTitleChange}
        onDescriptionChange={handleDescriptionChange}
      />
    );

    fireEvent.change(screen.getAllByPlaceholderText('Título ainda não gerado para esta posição.')[0], {
      target: { value: 'Título atualizado' },
    });
    fireEvent.change(screen.getByDisplayValue('Descrição inicial'), {
      target: { value: 'Descrição atualizada' },
    });

    expect(handleTitleChange).toHaveBeenCalledWith(0, 'Título atualizado');
    expect(handleDescriptionChange).toHaveBeenCalledWith('Descrição atualizada');
  });
});
