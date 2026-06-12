{# Surrogate keys shared across the intermediate and mart layers. Every model
   that emits a person_key / candidacy_key / donor_key must build it through
   these macros so the keys join across models. #}

{% macro person_key(source_prefix, id_col) -%}
    md5('{{ source_prefix }}:' || {{ id_col }})
{%- endmacro %}

{% macro candidacy_key(source_prefix, id_col, cycle_col) -%}
    md5('{{ source_prefix }}:' || {{ id_col }} || ':' || {{ cycle_col }}::string)
{%- endmacro %}

{# FEC-standard fuzzy donor identity: name + zip + employer. Imperfect but
   consistent across sources. #}
{% macro donor_key(name_col, zip_col, employer_col) -%}
    md5(
        upper(trim(coalesce({{ name_col }}, '')))
        || '|' || coalesce({{ zip_col }}, '')
        || '|' || upper(trim(coalesce({{ employer_col }}, '')))
    )
{%- endmacro %}
