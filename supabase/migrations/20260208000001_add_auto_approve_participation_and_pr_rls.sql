-- Add auto-approve flag for study-scoped join funnels

alter table public.studies
add column if not exists auto_approve_participation boolean not null default false;

-- Default auto-approve for SLP 2026 join flow
update public.studies
set auto_approve_participation = true
where join_flow_key = 'slp-2026';

-- Tighten participant participation_requests policies to prevent arbitrary status escalation

-- Replace overly-permissive participant policies
DROP POLICY IF EXISTS "Users can create own participation requests" ON public.participation_requests;
DROP POLICY IF EXISTS "Users can update own participation requests" ON public.participation_requests;

-- Helper for safe update checks (avoids relying on OLD in RLS)
create or replace function public.participant_can_update_participation_request(
  pr_id bigint,
  new_status text,
  new_consent_acknowledged_at timestamptz
)
returns boolean
language plpgsql
security definer
set search_path = public, pg_temp
as $$
declare
  pr record;
  is_auto_approve boolean;
begin
  select id, user_id, study_id, status, consent_acknowledged_at
  into pr
  from public.participation_requests
  where id = pr_id
  limit 1;

  if pr.id is null then
    return false;
  end if;

  if pr.user_id <> auth.uid() then
    return false;
  end if;

  select coalesce(s.auto_approve_participation, false)
  into is_auto_approve
  from public.studies s
  where s.id = pr.study_id;

  -- Allow no-op updates (e.g., updating non-sensitive fields)
  if new_status = pr.status and new_consent_acknowledged_at is not distinct from pr.consent_acknowledged_at then
    return true;
  end if;

  -- Allow participant withdrawal
  if new_status = 'withdrawn' then
    return true;
  end if;

  -- Allow pending -> approved only for auto-approve studies
  if pr.status = 'pending' and new_status = 'approved' and is_auto_approve then
    return true;
  end if;

  -- Allow acknowledging consent only after approved
  if pr.consent_acknowledged_at is null
     and new_consent_acknowledged_at is not null
     and new_status = pr.status
     and pr.status = 'approved' then
    return true;
  end if;

  return false;
end;
$$;

-- INSERT: participant can insert pending always; approved only for auto-approve studies
CREATE POLICY "Participants can insert participation requests (restricted)"
  ON public.participation_requests FOR INSERT
  TO authenticated
  WITH CHECK (
    auth.uid() = user_id
    AND (
      status = 'pending'
      OR (
        status = 'approved'
        AND EXISTS (
          SELECT 1
          FROM public.studies s
          WHERE s.id = participation_requests.study_id
          AND s.auto_approve_participation = true
        )
      )
    )
  );

-- UPDATE: participant can only perform restricted transitions + consent ack
CREATE POLICY "Participants can update participation requests (restricted)"
  ON public.participation_requests FOR UPDATE
  TO authenticated
  USING (auth.uid() = user_id)
  WITH CHECK (
    public.participant_can_update_participation_request(
      participation_requests.id,
      participation_requests.status,
      participation_requests.consent_acknowledged_at
    )
  );
