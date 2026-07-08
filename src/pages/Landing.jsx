import { Link } from 'react-router-dom'
import {
  LayoutDashboard, KanbanSquare, Users, ShieldCheck, BarChart3, Zap,
  CheckCircle2, ArrowRight,
} from 'lucide-react'
import { useAuth } from '../context/AuthContext'

const FEATURES = [
  {
    icon: LayoutDashboard,
    title: 'Live Dashboard',
    description: 'Open tasks, completion trends, and overdue work at a glance -- no digging through spreadsheets.',
  },
  {
    icon: KanbanSquare,
    title: 'Drag-and-Drop Kanban',
    description: 'Move work through To Do, In Progress, and Done with a board that feels instant.',
  },
  {
    icon: Users,
    title: 'Team Collaboration',
    description: 'Invite teammates by email, assign tasks, and see who owns what -- all in one place.',
  },
  {
    icon: ShieldCheck,
    title: 'Secure by Default',
    description: 'JWT-based auth and per-project permissions keep your team\'s data scoped to the right people.',
  },
  {
    icon: BarChart3,
    title: 'Progress at a Glance',
    description: 'Per-project progress bars and status breakdowns so nothing falls through the cracks.',
  },
  {
    icon: Zap,
    title: 'Built to Move Fast',
    description: 'A modern React + Django stack means the product stays snappy as your team grows.',
  },
]

const TESTIMONIALS = [
  {
    quote: 'We replaced three different tools with TeamFlow in a single afternoon. The kanban board alone paid for itself.',
    name: 'Amara O.',
    role: 'Product Manager, Fintech Startup',
  },
  {
    quote: "Finally a task tracker my whole team actually opens every day instead of avoiding.",
    name: 'Daniel K.',
    role: 'Engineering Lead',
  },
  {
    quote: 'Simple, fast, and it just works. Onboarding new teammates takes minutes.',
    name: 'Priya S.',
    role: 'Operations Manager',
  },
]

const PLANS = [
  {
    name: 'Free',
    price: '$0',
    period: 'forever',
    description: 'For individuals getting organized.',
    features: ['Up to 3 projects', 'Unlimited tasks', 'Kanban board', 'Basic dashboard'],
    cta: 'Get started',
    highlighted: false,
  },
  {
    name: 'Team',
    price: '$12',
    period: 'per user / month',
    description: 'For teams that ship together.',
    features: ['Unlimited projects', 'Team member invites', 'Assignee tracking', 'Priority support'],
    cta: 'Start free trial',
    highlighted: true,
  },
  {
    name: 'Enterprise',
    price: 'Contact us',
    period: '',
    description: 'For organizations with custom needs.',
    features: ['SSO & advanced security', 'Dedicated support', 'Custom integrations', 'SLA guarantees'],
    cta: 'Contact sales',
    highlighted: false,
  },
]

export default function Landing() {
  const { isAuthenticated } = useAuth()

  return (
    <div className="bg-white text-slate-900">
      {/* Nav */}
      <header className="border-b border-slate-100">
        <div className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-2 font-bold text-lg">
            <div className="h-8 w-8 rounded-lg bg-gradient-to-br from-brand-500 to-brand-700 flex items-center justify-center text-white">
              T
            </div>
            TeamFlow
          </div>
          <nav className="flex items-center gap-3">
            {isAuthenticated ? (
              <Link
                to="/dashboard"
                className="px-4 py-2 rounded-lg bg-brand-600 hover:bg-brand-700 text-white text-sm font-medium"
              >
                Go to Dashboard
              </Link>
            ) : (
              <>
                <Link to="/login" className="text-sm font-medium text-slate-600 hover:text-slate-900">
                  Login
                </Link>
                <Link
                  to="/signup"
                  className="px-4 py-2 rounded-lg bg-brand-600 hover:bg-brand-700 text-white text-sm font-medium"
                >
                  Get Started Free
                </Link>
              </>
            )}
          </nav>
        </div>
      </header>

      {/* Hero */}
      <section className="max-w-6xl mx-auto px-6 pt-20 pb-16 text-center">
        <span className="inline-block text-xs font-semibold uppercase tracking-wide text-brand-600 bg-brand-50 rounded-full px-3 py-1">
          Project & task management, without the bloat
        </span>
        <h1 className="mt-6 text-4xl sm:text-5xl font-bold tracking-tight max-w-3xl mx-auto">
          Run your team's work in one place, not five.
        </h1>
        <p className="mt-5 text-lg text-slate-500 max-w-2xl mx-auto">
          TeamFlow gives you a real-time dashboard, a drag-and-drop kanban board, and simple
          team assignment -- so your team spends time doing the work, not managing the tool.
        </p>
        <div className="mt-8 flex items-center justify-center gap-3">
          <Link
            to={isAuthenticated ? '/dashboard' : '/signup'}
            className="inline-flex items-center gap-2 px-6 py-3 rounded-lg bg-brand-600 hover:bg-brand-700 text-white font-medium"
          >
            {isAuthenticated ? 'Go to Dashboard' : 'Get Started Free'}
            <ArrowRight className="w-4 h-4" />
          </Link>
          {!isAuthenticated && (
            <Link
              to="/login"
              className="inline-flex items-center gap-2 px-6 py-3 rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-700 font-medium"
            >
              Login
            </Link>
          )}
        </div>
      </section>

      {/* Product preview (stylized, not a real screenshot) */}
      <section className="max-w-5xl mx-auto px-6 pb-20">
        <div className="rounded-2xl border border-slate-200 shadow-xl overflow-hidden bg-slate-50">
          <div className="h-10 bg-slate-100 border-b border-slate-200 flex items-center gap-1.5 px-4">
            <span className="h-2.5 w-2.5 rounded-full bg-red-300" />
            <span className="h-2.5 w-2.5 rounded-full bg-amber-300" />
            <span className="h-2.5 w-2.5 rounded-full bg-green-300" />
          </div>
          <div className="grid grid-cols-3 gap-4 p-6">
            {['To Do', 'In Progress', 'Done'].map((col, i) => (
              <div key={col} className="bg-white rounded-xl border border-slate-200 p-3">
                <p className="text-xs font-semibold text-slate-500 mb-3">{col}</p>
                <div className="space-y-2">
                  {Array.from({ length: 3 - i === 0 ? 1 : 3 - i }).map((_, j) => (
                    <div key={j} className="h-12 rounded-lg bg-slate-100 border border-slate-200" />
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Features */}
      <section className="bg-slate-50 py-20">
        <div className="max-w-6xl mx-auto px-6">
          <div className="text-center max-w-xl mx-auto mb-12">
            <h2 className="text-3xl font-bold">Everything your team actually uses</h2>
            <p className="mt-3 text-slate-500">No feature bloat -- just the tools that keep work moving.</p>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
            {FEATURES.map((f) => (
              <div key={f.title} className="bg-white rounded-xl border border-slate-200 p-6">
                <div className="h-10 w-10 rounded-lg bg-brand-50 text-brand-600 flex items-center justify-center mb-4">
                  <f.icon className="w-5 h-5" />
                </div>
                <h3 className="font-semibold text-slate-900">{f.title}</h3>
                <p className="text-sm text-slate-500 mt-1.5">{f.description}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Testimonials */}
      <section className="py-20">
        <div className="max-w-6xl mx-auto px-6">
          <div className="text-center max-w-xl mx-auto mb-12">
            <h2 className="text-3xl font-bold">Teams like yours use TeamFlow</h2>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-6">
            {TESTIMONIALS.map((t) => (
              <div key={t.name} className="bg-white rounded-xl border border-slate-200 p-6">
                <p className="text-sm text-slate-600 leading-relaxed">&ldquo;{t.quote}&rdquo;</p>
                <div className="mt-4">
                  <p className="text-sm font-semibold text-slate-900">{t.name}</p>
                  <p className="text-xs text-slate-500">{t.role}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Pricing */}
      <section className="bg-slate-50 py-20">
        <div className="max-w-6xl mx-auto px-6">
          <div className="text-center max-w-xl mx-auto mb-12">
            <h2 className="text-3xl font-bold">Simple, transparent pricing</h2>
            <p className="mt-3 text-slate-500">Start free. Upgrade when your team grows.</p>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-6 items-start">
            {PLANS.map((plan) => (
              <div
                key={plan.name}
                className={`rounded-xl border p-6 flex flex-col ${
                  plan.highlighted
                    ? 'border-brand-500 shadow-lg bg-white relative sm:-translate-y-2'
                    : 'border-slate-200 bg-white'
                }`}
              >
                {plan.highlighted && (
                  <span className="absolute -top-3 left-1/2 -translate-x-1/2 text-[10px] font-semibold uppercase tracking-wide bg-brand-600 text-white rounded-full px-3 py-1">
                    Most popular
                  </span>
                )}
                <h3 className="font-semibold text-slate-900">{plan.name}</h3>
                <p className="text-xs text-slate-500 mt-1">{plan.description}</p>
                <div className="mt-4">
                  <span className="text-3xl font-bold text-slate-900">{plan.price}</span>
                  {plan.period && <span className="text-sm text-slate-500 ml-1">{plan.period}</span>}
                </div>
                <ul className="mt-6 space-y-2 flex-1">
                  {plan.features.map((f) => (
                    <li key={f} className="flex items-start gap-2 text-sm text-slate-600">
                      <CheckCircle2 className="w-4 h-4 text-brand-600 mt-0.5 shrink-0" />
                      {f}
                    </li>
                  ))}
                </ul>
                <Link
                  to="/signup"
                  className={`mt-6 text-center px-4 py-2 rounded-lg text-sm font-medium ${
                    plan.highlighted
                      ? 'bg-brand-600 hover:bg-brand-700 text-white'
                      : 'bg-slate-100 hover:bg-slate-200 text-slate-700'
                  }`}
                >
                  {plan.cta}
                </Link>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="py-20">
        <div className="max-w-3xl mx-auto px-6 text-center">
          <h2 className="text-3xl font-bold">Ready to get your team organized?</h2>
          <p className="mt-3 text-slate-500">Free to start. No credit card required.</p>
          <Link
            to="/signup"
            className="mt-8 inline-flex items-center gap-2 px-6 py-3 rounded-lg bg-brand-600 hover:bg-brand-700 text-white font-medium"
          >
            Get Started Free
            <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
      </section>

      <footer className="border-t border-slate-100 py-8">
        <div className="max-w-6xl mx-auto px-6 text-sm text-slate-400 text-center">
          &copy; {new Date().getFullYear()} TeamFlow. All rights reserved.
        </div>
      </footer>
    </div>
  )
}