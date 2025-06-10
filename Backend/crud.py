from .crud_users import (
    get_user,
    get_user_by_email,
    get_users,
    create_user,
    update_user,
    delete_user,
    create_user_oauth,
    get_user_by_provider,
    set_user_password_reset_token,
    get_user_by_reset_token,
    get_role,
    get_role_by_name,
    get_roles,
    create_role,
    get_plano,
    get_plano_by_name,
    get_planos,
    create_plano,
    update_plano,
    delete_plano,
)

from .crud_fornecedores import (
    create_fornecedor,
    get_fornecedor,
    get_fornecedores_by_user,
    count_fornecedores_by_user,
    update_fornecedor,
    delete_fornecedor,
)

from .crud_produtos import (
    create_produto,
    create_produtos_bulk,
    get_produto,
    get_produtos_by_user,
    count_produtos_by_user,
    update_produto,
    delete_produto,
    save_produto_image,
)

from .crud_product_types import (
    create_product_type,
    get_product_type,
    get_product_type_by_key_name,
    get_product_types_for_user,
    count_product_types_for_user,
    update_product_type,
    delete_product_type,
    create_attribute_template,
    get_attribute_template,
    update_attribute_template,
    delete_attribute_template,
    reorder_attribute_template,
)

from .crud_registros_uso_ia import (
    create_registro_uso_ia,
    get_registros_uso_ia,
    count_registros_uso_ia,
    get_usos_ia_by_produto,
    count_usos_ia_by_user_and_type_no_mes_corrente,
    get_geracoes_ia_count_no_mes_corrente,
)

from .crud_historico import (
    create_registro_historico,
    get_registros_historico,
    count_registros_historico,
)

from .initial_data import create_initial_data
