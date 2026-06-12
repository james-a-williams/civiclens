{# Route models with a +schema config to exactly that schema (STAGING /
   INTERMEDIATE / MARTS are pre-created), instead of dbt's default
   <target_schema>_<custom_schema> concatenation. #}
{% macro generate_schema_name(custom_schema_name, node) -%}
    {%- if custom_schema_name is none -%}
        {{ target.schema }}
    {%- else -%}
        {{ custom_schema_name | trim }}
    {%- endif -%}
{%- endmacro %}
