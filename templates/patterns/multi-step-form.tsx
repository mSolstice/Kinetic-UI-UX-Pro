import { useId, useState } from 'react';
import './multi-step-form.css';

type Step = 'account' | 'profile' | 'review';
type FormState =
  | { status: 'idle' }
  | { status: 'loading' }
  | { status: 'success'; message: string }
  | { status: 'error'; message: string };

const STEPS: Step[] = ['account', 'profile', 'review'];

export function MultiStepFormPattern() {
  const errorId = useId();
  const statusId = useId();
  const [stepIndex, setStepIndex] = useState(0);
  const [state, setState] = useState<FormState>({ status: 'idle' });
  const [locked, setLocked] = useState(false);
  const [values, setValues] = useState({ email: '', name: '', plan: '' });
  const step = STEPS[stepIndex];
  const empty = !values.email && !values.name && !values.plan;

  function update(field: keyof typeof values, value: string) {
    setValues((current) => ({ ...current, [field]: value }));
    if (state.status === 'error') setState({ status: 'idle' });
  }

  function next() {
    if (step === 'account' && !values.email) {
      setState({ status: 'error', message: 'Add an email address to continue.' });
      return;
    }
    if (step === 'profile' && !values.name) {
      setState({ status: 'error', message: 'Add a display name to continue.' });
      return;
    }
    setStepIndex((index) => Math.min(index + 1, STEPS.length - 1));
  }

  function submit() {
    if (state.status === 'loading' || locked) return;
    if (!values.plan) {
      setState({ status: 'error', message: 'Choose a plan before submitting.' });
      return;
    }
    setState({ status: 'loading' });
    window.setTimeout(() => setState({ status: 'success', message: 'Account created.' }), 0);
  }

  return (
    <form
      className="kp-form"
      noValidate
      aria-busy={state.status === 'loading'}
      aria-describedby={`${statusId} ${state.status === 'error' ? errorId : ''}`}
      data-state={empty ? 'empty' : state.status}
      onSubmit={(event) => {
        event.preventDefault();
        submit();
      }}
    >
      <header className="kp-form__header">
        <h2>Create account</h2>
        <p>Step {stepIndex + 1} of {STEPS.length}</p>
      </header>

      <ol className="kp-form__steps" aria-label="Progress">
        {STEPS.map((item, index) => (
          <li key={item} aria-current={item === step ? 'step' : undefined}>
            {item}
          </li>
        ))}
      </ol>

      <div id={statusId} className="kp-form__status" aria-live="polite">
        {state.status === 'loading' ? 'Submitting account.' : ''}
        {state.status === 'success' ? state.message : ''}
      </div>
      <div id={errorId} className="kp-form__error" role="alert" aria-live="polite">
        {state.status === 'error' ? state.message : ''}
      </div>

      {empty && (
        <div className="kp-form__empty">
          Start with an email address. Your progress remains visible as you move through the form.
        </div>
      )}

      {step === 'account' && (
        <label className="kp-form__field">
          <span>Email</span>
          <input
            type="email"
            autoComplete="email"
            value={values.email}
            onChange={(event) => update('email', event.currentTarget.value)}
          />
        </label>
      )}

      {step === 'profile' && (
        <label className="kp-form__field">
          <span>Display name</span>
          <input
            type="text"
            autoComplete="name"
            value={values.name}
            onChange={(event) => update('name', event.currentTarget.value)}
          />
        </label>
      )}

      {step === 'review' && (
        <fieldset className="kp-form__field">
          <legend>Plan</legend>
          <label>
            <input
              type="radio"
              name="plan"
              value="starter"
              autoComplete="off"
              checked={values.plan === 'starter'}
              onChange={(event) => update('plan', event.currentTarget.value)}
            />
            Starter
          </label>
          <label>
            <input
              type="radio"
              name="plan"
              value="team"
              autoComplete="off"
              checked={values.plan === 'team'}
              onChange={(event) => update('plan', event.currentTarget.value)}
            />
            Team
          </label>
        </fieldset>
      )}

      <footer className="kp-form__actions">
        <button type="button" className="kp-form__secondary" onClick={() => setStepIndex((index) => Math.max(index - 1, 0))}>
          Back
        </button>
        <button type="button" className="kp-form__secondary" aria-pressed={locked} onClick={() => setLocked((value) => !value)}>
          {locked ? 'Enable submit' : 'Disable submit'}
        </button>
        {step === 'review' ? (
          <button type="submit" className="kp-form__primary" aria-disabled={state.status === 'loading' || locked}>
            {state.status === 'loading' ? 'Submitting' : 'Submit'}
          </button>
        ) : (
          <button type="button" className="kp-form__primary" onClick={next}>
            Continue
          </button>
        )}
      </footer>
    </form>
  );
}
