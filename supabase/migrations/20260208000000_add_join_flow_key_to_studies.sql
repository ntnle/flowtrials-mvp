-- Add study-level join flow selector

alter table public.studies
add column if not exists join_flow_key text;
