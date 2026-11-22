-- Gold: dimensão de forma de pagamento (SCD 1, estática). Valores do enum PaymentMethod.
select cast(sk_forma_pagamento as integer) as sk_forma_pagamento,
       cast(nome_forma_pagamento as varchar) as nome_forma_pagamento,
       cast(grupo_forma_pagamento as varchar) as grupo_forma_pagamento
from (values
    (-1, 'NÃO IDENTIFICADO', 'não identificado'),
    (1, 'PIX', 'pix'),
    (2, 'CREDITO', 'cartão'),
    (3, 'DEBITO', 'cartão')
) as t(sk_forma_pagamento, nome_forma_pagamento, grupo_forma_pagamento)
