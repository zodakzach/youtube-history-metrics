import { useMemo, useState } from 'react'
import type { ChangeEvent, FormEvent } from 'react'

type UploadStatus = 'idle' | 'uploading' | 'success' | 'error'

type StepId = 'verify' | 'request' | 'loaded'

type Step = {
  id: StepId
  label: string
  blurb: string
  state: StepState
}

type StepState = 'upcoming' | 'active' | 'complete' | 'error'

type Feature = {
  title: string
  body: string
}

const BASE_STEPS: Omit<Step, 'state'>[] = [
  {
    id: 'verify',
    label: 'Verifying & Extracting',
    blurb: 'We parse your file, clean the entries, and prep them for enrichment.',
  },
  {
    id: 'request',
    label: 'Requesting Video Data',
    blurb: 'Video metadata gets requested from YouTube for richer analytics.',
  },
  {
    id: 'loaded',
    label: 'Data Loaded',
    blurb: 'Dive into watch streaks, channel stats, and viewing patterns.',
  },
]

const FEATURES: Feature[] = [
  {
    title: 'Secure by design',
    body: 'Uploads are processed in memory and tied to a short-lived session stored in Redis.',
  },
  {
    title: 'Actionable analytics',
    body: 'Surface your viewing trends, longest streaks, and favorite creators with one click.',
  },
  {
    title: 'HTMX + React ready',
    body: 'Share the same pipeline that powers the HTMX UI, now refactored into a modern React flow.',
  },
]

const API_ENDPOINT = import.meta.env.VITE_BACKEND_URL ?? 'http://localhost:8000/loadData'

function App() {
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [status, setStatus] = useState<UploadStatus>('idle')
  const [message, setMessage] = useState<string | null>(null)

  const steps: Step[] = useMemo(() => {
    const resolveState = (stepId: StepId): StepState => {
      switch (status) {
        case 'uploading':
          return stepId === 'verify' ? 'active' : 'upcoming'
        case 'success':
          if (stepId === 'loaded') return 'active'
          return 'complete'
        case 'error':
          return stepId === 'verify' ? 'error' : 'upcoming'
        default:
          return 'upcoming'
      }
    }

    return BASE_STEPS.map((step) => ({
      ...step,
      state: resolveState(step.id),
    }))
  }, [status])

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (!selectedFile) {
      setMessage('Select your YouTube watch-history JSON file to continue.')
      return
    }

    setStatus('uploading')
    setMessage(null)

    try {
      const formData = new FormData()
      formData.append('file_input', selectedFile)

      const response = await fetch(API_ENDPOINT, {
        method: 'POST',
        body: formData,
        credentials: 'include',
      })

      if (!response.ok) {
        throw new Error('Upload failed — make sure the FastAPI backend is running.')
      }

      setStatus('success')
      setMessage('History uploaded. Continue to the analytics dashboard to explore your data.')
    } catch (error) {
      setStatus('error')
      setMessage(
        error instanceof Error
          ? error.message
          : 'Something went wrong while uploading. Please try again.',
      )
    }
  }

  const handleFileChange = (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0] ?? null
    setSelectedFile(file)
    setStatus('idle')
    setMessage(null)
  }

  return (
    <div className="min-h-screen bg-slate-950 text-white">
      <header className="border-b border-white/10 bg-slate-950/80 backdrop-blur">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-4">
          <div>
            <p className="text-xs uppercase tracking-[0.4em] text-emerald-300">YouTube History Metrics</p>
            <p className="text-sm text-slate-300">FastAPI · HTMX · React</p>
          </div>
          <a
            href="https://github.com/zodakzach/youtube-history-metrics"
            className="hidden items-center gap-2 rounded-full border border-white/15 px-4 py-2 text-sm text-slate-200 transition hover:border-emerald-300 hover:text-emerald-200 sm:flex"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              className="h-4 w-4"
            >
              <path d="M9 18l6-6-6-6" />
            </svg>
            View Source
          </a>
        </div>
      </header>

      <main className="px-4">
        <section className="mx-auto max-w-5xl py-12 lg:min-h-[75vh] lg:py-20">
          <div className="text-center">
            <h1 className="text-4xl font-semibold leading-tight text-white md:text-5xl">
              Select Your YouTube Watch-History JSON File
            </h1>
            <p className="mt-5 text-base text-slate-300 md:text-lg">
              Upload the takeout file you downloaded from Google to kick off the ingestion pipeline. We&apos;ll verify
              the contents, request additional video metadata, and unlock the analytics experience powered by FastAPI.
            </p>
          </div>

          <form
            onSubmit={handleSubmit}
            className="mt-12 rounded-3xl border border-white/10 bg-slate-900/50 p-6 shadow-2xl shadow-emerald-500/10 backdrop-blur"
          >
            <div className="flex flex-col gap-5 md:flex-row md:items-center">
              <div className="flex-1">
                <label
                  htmlFor="history-file"
                  className="text-sm font-semibold text-slate-200"
                >
                  Watch History JSON
                </label>
                <input
                  id="history-file"
                  name="file_input"
                  type="file"
                  accept=".json,application/json"
                  onChange={handleFileChange}
                  className="mt-3 w-full rounded-2xl border border-white/15 bg-slate-950/70 px-4 py-3 text-sm text-slate-50 file:mr-4 file:cursor-pointer file:rounded-lg file:border-0 file:bg-emerald-500/10 file:px-4 file:py-2 file:text-emerald-200 focus:border-emerald-400 focus:outline-none focus:ring-2 focus:ring-emerald-500/40"
                />
                {selectedFile && (
                  <p className="mt-2 text-xs text-slate-400">Selected: {selectedFile.name}</p>
                )}
              </div>
              <button
                type="submit"
                className="flex items-center justify-center rounded-2xl bg-emerald-400 px-8 py-4 text-sm font-semibold uppercase tracking-wide text-slate-950 transition hover:bg-emerald-300 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-200"
              >
                Load Data
              </button>
            </div>

            <p className="mt-4 text-sm text-slate-400">
              Need help exporting from Google Takeout?{' '}
              <a
                href="/instructions"
                className="text-emerald-300 underline-offset-4 transition hover:text-emerald-200 hover:underline"
              >
                Click here
              </a>{' '}
              for the walkthrough.
            </p>
          </form>

          <UploadFeedback
            message={message}
            status={status}
          />

          <StepList steps={steps} />
        </section>

        <section className="mx-auto grid max-w-5xl gap-6 border-t border-white/10 py-12 md:grid-cols-3">
          {FEATURES.map((feature) => (
            <article
              key={feature.title}
              className="rounded-2xl border border-white/10 bg-slate-900/40 p-6 shadow-lg shadow-black/20"
            >
              <h3 className="text-lg font-semibold text-white">{feature.title}</h3>
              <p className="mt-3 text-sm text-slate-300">{feature.body}</p>
            </article>
          ))}
        </section>
      </main>

      <footer className="border-t border-white/5 py-6 text-center text-xs text-slate-500">
        Built with FastAPI · Redis · React · TailwindCSS
      </footer>
    </div>
  )
}

function UploadFeedback({ status, message }: { status: UploadStatus; message: string | null }) {
  if (status === 'idle' && !message) return null

  if (status === 'uploading') {
    return (
      <div className="mt-8 flex items-center justify-center gap-3 rounded-2xl border border-white/10 bg-slate-900/40 px-4 py-3 text-sm text-slate-200">
        <svg
          className="h-5 w-5 animate-spin text-emerald-300"
          viewBox="0 0 24 24"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
        >
          <circle
            className="opacity-25"
            cx="12"
            cy="12"
            r="10"
            stroke="currentColor"
            strokeWidth="4"
          />
          <path
            className="opacity-75"
            fill="currentColor"
            d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z"
          />
        </svg>
        Uploading your file…
      </div>
    )
  }

  if (!message) return null

  return (
    <p
      className={`mt-8 rounded-2xl border px-4 py-3 text-center text-sm ${
        status === 'error'
          ? 'border-rose-400/40 bg-rose-500/10 text-rose-100'
          : 'border-emerald-400/40 bg-emerald-500/10 text-emerald-100'
      }`}
    >
      {message}
    </p>
  )
}

function StepList({ steps }: { steps: Step[] }) {
  return (
    <ol className="mt-12 flex flex-col gap-6 lg:flex-row lg:items-start lg:justify-between">
      {steps.map((step, index) => (
        <li
          key={step.id}
          className="flex flex-1 items-start gap-4 rounded-2xl border border-white/10 bg-slate-900/30 p-5"
        >
          <span className={getStepClass(step.state)}>
            {step.state === 'complete' ? (
              <svg
                xmlns="http://www.w3.org/2000/svg"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                className="h-6 w-6"
              >
                <path d="M5 13l4 4L19 7" />
              </svg>
            ) : (
              index + 1
            )}
          </span>
          <div>
            <h3 className="text-base font-semibold text-white">{step.label}</h3>
            <p className="mt-2 text-sm text-slate-300">{step.blurb}</p>
          </div>
        </li>
      ))}
    </ol>
  )
}

function getStepClass(state: StepState) {
  const base = 'flex h-12 w-12 items-center justify-center rounded-full border-2 text-lg font-semibold'
  if (state === 'complete') return `${base} border-emerald-300 bg-emerald-400/20 text-emerald-100`
  if (state === 'active') return `${base} border-emerald-400 bg-emerald-400/10 text-emerald-50`
  if (state === 'error') return `${base} border-rose-400 bg-rose-400/10 text-rose-100`
  return `${base} border-white/30 text-slate-300`
}

export default App

