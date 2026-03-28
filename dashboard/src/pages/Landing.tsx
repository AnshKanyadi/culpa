import React from 'react'
import { Link } from 'react-router-dom'
import { Check, X, ArrowRight, Github } from 'lucide-react'
import { cn } from '../lib/utils'
import { Logo } from '../components/Logo'

function Hero() {
  return (
    <section className="relative pt-32 pb-24 px-6 overflow-hidden">
      <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[800px] h-[600px] bg-culpa-red/[0.04] rounded-full blur-[120px] pointer-events-none" />

      <div className="relative max-w-3xl mx-auto text-center">
        <h1 className="text-4xl sm:text-5xl lg:text-6xl font-bold text-white tracking-tight leading-[1.1]">
          Stop guessing why your AI agent broke production.
        </h1>
        <p className="mt-6 text-lg sm:text-xl text-culpa-text-dim max-w-2xl mx-auto leading-relaxed">
          Culpa records every AI agent decision with full fidelity. Replay failures deterministically.
          Fork at any point to test what-if scenarios. Zero API cost.
        </p>
        <div className="mt-10 flex flex-col sm:flex-row items-center justify-center gap-4">
          <Link
            to="/register"
            className="flex items-center gap-2 px-6 py-3 bg-culpa-red hover:bg-[#ef4444] text-white font-semibold
                       text-sm rounded-lg transition-colors"
          >
            Get Started Free <ArrowRight size={16} />
          </Link>
          <a
            href="https://github.com/AnshKanyadi/prismo"
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-2 px-6 py-3 border border-culpa-border text-culpa-text
                       font-medium text-sm rounded-lg hover:bg-culpa-surface transition-colors"
          >
            <Github size={16} /> View on GitHub
          </a>
        </div>
      </div>
    </section>
  )
}

const PROBLEMS = [
  {
    title: 'Your AI agent deleted the wrong files',
    desc: "Can't reproduce it. Re-running gives completely different behavior. The chain of reasoning that caused the failure is gone.",
  },
  {
    title: 'You stare at the trace for hours',
    desc: "Observability tools show you what happened. But a trace doesn't explain why the agent made that particular decision at step 3.",
  },
  {
    title: 'You guess at a fix and pray',
    desc: "There's no way to test if your prompt change actually prevents the failure. You just re-run and hope.",
  },
]

function ProblemSection() {
  return (
    <section className="py-24 px-6">
      <div className="max-w-5xl mx-auto">
        <h2 className="text-2xl sm:text-3xl font-bold text-white text-center mb-4">
          Debugging AI agents is broken
        </h2>
        <p className="text-culpa-text-dim text-center max-w-xl mx-auto mb-16">
          When an AI coding agent causes a problem, you have no way to understand why or prevent it from happening again.
        </p>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {PROBLEMS.map((p) => (
            <div
              key={p.title}
              className="bg-culpa-surface border border-culpa-border rounded-2xl p-6"
            >
              <h3 className="text-sm font-semibold text-white mb-3">{p.title}</h3>
              <p className="text-sm text-culpa-text-dim leading-relaxed">{p.desc}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}

const STEPS = [
  {
    step: '01',
    title: 'Record',
    code: `import culpa\nculpa.init("Fix auth bug")\n\n# your agent runs here\n# every LLM call captured\n\nsession = culpa.stop()`,
    desc: 'One line. Transparent interception of all Anthropic and OpenAI SDK calls, file changes, and terminal commands.',
  },
  {
    step: '02',
    title: 'Replay',
    code: `culpa replay abc123\n\n# Deterministic re-execution\n# Uses recorded responses\n# Zero API calls\n# Identical behavior`,
    desc: 'Re-execute the exact failure path using recorded LLM responses as stubs. No API costs, identical behavior every time.',
  },
  {
    step: '03',
    title: 'Fork',
    code: `forker = CulpaForker(session)\nresult = forker.fork_at(\n  event_id="01HN...",\n  new_response="Keep bcrypt."\n)\nprint(result.divergence_summary)`,
    desc: 'Pick any LLM call, inject a different response, and see what would have happened. Answer "what if?" without re-running.',
  },
]

function HowItWorksSection() {
  return (
    <section className="py-24 px-6 border-t border-culpa-border">
      <div className="max-w-5xl mx-auto">
        <h2 className="text-2xl sm:text-3xl font-bold text-white text-center mb-16">
          How it works
        </h2>
        <div className="space-y-20">
          {STEPS.map((s, i) => (
            <div
              key={s.step}
              className={cn(
                'flex flex-col gap-8',
                i % 2 === 0 ? 'md:flex-row' : 'md:flex-row-reverse',
              )}
            >
              <div className="flex-1 flex flex-col justify-center">
                <div className="flex items-center gap-3 mb-3">
                  <span className="text-xs font-mono text-culpa-red font-bold">{s.step}</span>
                  <h3 className="text-xl font-bold text-white">{s.title}</h3>
                </div>
                <p className="text-sm text-culpa-text-dim leading-relaxed">{s.desc}</p>
              </div>
              <div className="flex-1">
                <div className="bg-culpa-surface border border-culpa-border rounded-2xl overflow-hidden">
                  <div className="flex items-center gap-1.5 px-4 py-2.5 border-b border-culpa-border">
                    <div className="w-2.5 h-2.5 rounded-full bg-culpa-red/60" />
                    <div className="w-2.5 h-2.5 rounded-full bg-culpa-orange/60" />
                    <div className="w-2.5 h-2.5 rounded-full bg-culpa-green/60" />
                  </div>
                  <pre className="p-5 text-sm font-mono text-culpa-blue leading-relaxed overflow-x-auto">
                    {s.code}
                  </pre>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}

interface CompRow {
  feature: string
  culpa: boolean
  braintrust: boolean
  langgraph: boolean
  langfuse: boolean
}

const COMPARISON: CompRow[] = [
  { feature: 'Deterministic replay', culpa: true, braintrust: false, langgraph: false, langfuse: false },
  { feature: 'Counterfactual forking', culpa: true, braintrust: false, langgraph: false, langfuse: false },
  { feature: 'Framework-agnostic', culpa: true, braintrust: true, langgraph: false, langfuse: true },
  { feature: 'Zero replay cost', culpa: true, braintrust: false, langgraph: false, langfuse: false },
  { feature: 'File change tracking', culpa: true, braintrust: false, langgraph: false, langfuse: false },
  { feature: 'Terminal command capture', culpa: true, braintrust: false, langgraph: false, langfuse: false },
]

function Cell({ yes }: { yes: boolean }) {
  return yes
    ? <Check size={16} className="text-culpa-green mx-auto" />
    : <X size={16} className="text-culpa-text-dim/30 mx-auto" />
}

function ComparisonSection() {
  return (
    <section className="py-24 px-6 border-t border-culpa-border">
      <div className="max-w-3xl mx-auto">
        <h2 className="text-2xl sm:text-3xl font-bold text-white text-center mb-4">
          What makes Culpa different
        </h2>
        <p className="text-culpa-text-dim text-center max-w-xl mx-auto mb-12">
          Other tools show you traces. Culpa lets you replay and rewrite history.
        </p>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-culpa-border">
                <th className="py-3 px-4 text-left text-culpa-text-dim font-medium" />
                <th className="py-3 px-4 text-center font-bold text-culpa-red">Culpa</th>
                <th className="py-3 px-4 text-center text-culpa-text-dim font-medium">Braintrust</th>
                <th className="py-3 px-4 text-center text-culpa-text-dim font-medium">LangGraph</th>
                <th className="py-3 px-4 text-center text-culpa-text-dim font-medium">Langfuse</th>
              </tr>
            </thead>
            <tbody>
              {COMPARISON.map((row) => (
                <tr key={row.feature} className="border-b border-culpa-border/50">
                  <td className="py-3 px-4 text-culpa-text">{row.feature}</td>
                  <td className="py-3 px-4"><Cell yes={row.culpa} /></td>
                  <td className="py-3 px-4"><Cell yes={row.braintrust} /></td>
                  <td className="py-3 px-4"><Cell yes={row.langgraph} /></td>
                  <td className="py-3 px-4"><Cell yes={row.langfuse} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </section>
  )
}

function CodeSection() {
  return (
    <section className="py-24 px-6 border-t border-culpa-border">
      <div className="max-w-2xl mx-auto text-center">
        <h2 className="text-2xl sm:text-3xl font-bold text-white mb-4">
          Three lines to start
        </h2>
        <p className="text-culpa-text-dim mb-10">
          No config files, no framework integration, no setup wizard.
        </p>
        <div className="bg-culpa-surface border border-culpa-border rounded-2xl overflow-hidden text-left">
          <div className="flex items-center gap-1.5 px-4 py-2.5 border-b border-culpa-border">
            <div className="w-2.5 h-2.5 rounded-full bg-culpa-red/60" />
            <div className="w-2.5 h-2.5 rounded-full bg-culpa-orange/60" />
            <div className="w-2.5 h-2.5 rounded-full bg-culpa-green/60" />
            <span className="ml-3 text-xs text-culpa-text-dim font-mono">my_agent.py</span>
          </div>
          <pre className="p-6 text-sm font-mono leading-relaxed overflow-x-auto">
            <span className="text-culpa-purple">import</span> <span className="text-culpa-blue">culpa</span>{'\n'}
            <span className="text-culpa-blue">culpa</span>.<span className="text-culpa-green">init</span>(){'\n'}
            <span className="text-culpa-text-dim"># that's it — every LLM call is now recorded</span>
          </pre>
        </div>

        <div className="mt-6 bg-culpa-surface border border-culpa-border rounded-2xl overflow-hidden text-left">
          <div className="flex items-center gap-1.5 px-4 py-2.5 border-b border-culpa-border">
            <span className="text-xs text-culpa-text-dim font-mono">terminal</span>
          </div>
          <pre className="p-6 text-sm font-mono leading-relaxed overflow-x-auto">
            <span className="text-culpa-text-dim">$</span> <span className="text-culpa-blue">culpa record</span> <span className="text-culpa-green">"Fix auth"</span> -- python agent.py{'\n'}
            <span className="text-culpa-text-dim">$</span> <span className="text-culpa-blue">culpa serve</span>
          </pre>
        </div>
      </div>
    </section>
  )
}

const FREE_FEATURES = [
  '3 cloud sessions',
  '7-day retention',
  '5 forks per session',
  'Local replay & fork',
  'Anthropic + OpenAI support',
]

const PRO_FEATURES = [
  'Unlimited cloud sessions',
  '90-day retention',
  'Unlimited fork history',
  'Team sharing',
  'Priority support',
]

function PricingSection() {
  return (
    <section className="py-24 px-6 border-t border-culpa-border">
      <div className="max-w-3xl mx-auto">
        <h2 className="text-2xl sm:text-3xl font-bold text-white text-center mb-4">
          Pricing
        </h2>
        <p className="text-culpa-text-dim text-center max-w-md mx-auto mb-12">
          Start free. Upgrade when you need more sessions and longer retention.
        </p>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="bg-culpa-surface border border-culpa-border rounded-2xl p-8">
            <h3 className="text-sm font-semibold text-culpa-text-dim uppercase tracking-wider">Free</h3>
            <div className="mt-2 mb-6">
              <span className="text-4xl font-bold text-white">$0</span>
            </div>
            <ul className="space-y-3 mb-8">
              {FREE_FEATURES.map((f) => (
                <li key={f} className="flex items-center gap-2.5 text-sm text-culpa-text-dim">
                  <Check size={14} className="text-culpa-text-dim shrink-0" /> {f}
                </li>
              ))}
            </ul>
            <Link
              to="/register"
              className="block w-full text-center py-2.5 border border-culpa-border text-culpa-text text-sm font-medium
                         rounded-lg hover:bg-culpa-muted transition-colors"
            >
              Get started
            </Link>
          </div>

          <div className="bg-culpa-surface border border-culpa-red/30 rounded-2xl p-8 relative">
            <div className="absolute -top-3 left-6 bg-culpa-red text-white text-[10px] font-bold uppercase tracking-wider px-2.5 py-1 rounded-full">
              Recommended
            </div>
            <h3 className="text-sm font-semibold text-culpa-text-dim uppercase tracking-wider">Pro</h3>
            <div className="mt-2 mb-6">
              <span className="text-4xl font-bold text-white">$29</span>
              <span className="text-sm text-culpa-text-dim ml-1">/ month</span>
            </div>
            <ul className="space-y-3 mb-8">
              {PRO_FEATURES.map((f) => (
                <li key={f} className="flex items-center gap-2.5 text-sm text-culpa-text">
                  <Check size={14} className="text-culpa-red shrink-0" /> {f}
                </li>
              ))}
            </ul>
            <Link
              to="/register"
              className="block w-full text-center py-2.5 bg-culpa-red hover:bg-[#ef4444] text-white text-sm font-semibold
                         rounded-lg transition-colors"
            >
              Get started
            </Link>
          </div>
        </div>
      </div>
    </section>
  )
}

function Footer() {
  return (
    <footer className="border-t border-culpa-border py-12 px-6">
      <div className="max-w-5xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-6">
        <div className="flex items-center gap-6">
          <Logo size="sm" linkTo="/" />
          <a
            href="https://github.com/AnshKanyadi/prismo"
            target="_blank"
            rel="noopener noreferrer"
            className="text-xs text-culpa-text-dim hover:text-culpa-text transition-colors flex items-center gap-1"
          >
            <Github size={12} /> GitHub
          </a>
          <a
            href="mailto:ansh@culpa.dev"
            className="text-xs text-culpa-text-dim hover:text-culpa-text transition-colors"
          >
            Contact
          </a>
        </div>
        <div className="flex items-center gap-4 text-xs text-culpa-text-dim">
          <span>Built by Ansh Kanyadi</span>
          <span className="text-culpa-border">·</span>
          <span>MIT License</span>
        </div>
      </div>
    </footer>
  )
}

function Nav() {
  return (
    <nav className="fixed top-0 inset-x-0 z-40 bg-culpa-bg/80 backdrop-blur-md border-b border-culpa-border/50">
      <div className="max-w-5xl mx-auto flex items-center justify-between px-6 py-3">
        <Logo size="md" linkTo="/" />
        <div className="flex items-center gap-3">
          <Link
            to="/login"
            className="text-sm text-culpa-text-dim hover:text-culpa-text transition-colors"
          >
            Sign in
          </Link>
          <Link
            to="/register"
            className="text-sm px-4 py-1.5 bg-culpa-red hover:bg-[#ef4444] text-white font-medium
                       rounded-lg transition-colors"
          >
            Get started
          </Link>
        </div>
      </div>
    </nav>
  )
}

export function Landing() {
  return (
    <div className="min-h-screen bg-culpa-bg">
      <Nav />
      <Hero />
      <ProblemSection />
      <HowItWorksSection />
      <ComparisonSection />
      <CodeSection />
      <PricingSection />
      <Footer />
    </div>
  )
}
