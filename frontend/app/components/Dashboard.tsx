'use client'

import { useState, useEffect, useCallback } from 'react'
import { useAuth } from '../../contexts/AuthContext'
import { buildUserHeadersFromToken, getValidSessionAccessToken } from '../../lib/sessionToken'
import Header from './Header'
import StepForm from './StepForm'
import UploadStep from './UploadStep'
import ModeSelection from './ModeSelection'
import ProcessingStep from './ProcessingStep'
import ResultStep from './ResultStep'
import {
  FileText,
  FileSpreadsheet,
  Download,
  Trash2,
  UserCircle2,
} from 'lucide-react'
import { UserDetails, ProcessingResult, ProcessingMode, Step, JobSubmitted, ProfileHistoryResponse } from '@/types'

const BANKS = [
  { name: 'HDFC Bank', available: true },
  { name: 'ICICI Bank', available: true },
  { name: 'Axis Bank', available: true },
  { name: 'Kotak Bank', available: true },
  { name: 'SBI', available: true },
  { name: 'PNB', available: false },
  { name: 'Bank of Baroda', available: false },
]

const APP_API_BASE = '/api'

export default function Dashboard() {
  const { user, logout } = useAuth()
  const [step, setStep] = useState<Step>(1)
  const [filesTab, setFilesTab] = useState<'uploaded' | 'reports'>('uploaded')
  const [isProfilePanelOpen, setIsProfilePanelOpen] = useState(false)
  const [selectedFiles, setSelectedFiles] = useState<Set<string>>(new Set())
  const [userDetails, setUserDetails] = useState<UserDetails>({
    fullName: '',
    accountType: '',
    bankName: '',
  })
  const [file, setFile] = useState<File | null>(null)
  const [pdfPassword, setPdfPassword] = useState<string | undefined>(undefined)
  const [mode, setMode] = useState<ProcessingMode>('free')
  const [apiKey, setApiKey] = useState('')
  const [jobId, setJobId] = useState<string | null>(null)
  const [result, setResult] = useState<ProcessingResult | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [isProcessing, setIsProcessing] = useState(false)
  const [historySummary, setHistorySummary] = useState<ProfileHistoryResponse['summary']>({
    total_uploads: 0,
    processed_files: 0,
    generated_reports: 0,
    latest_account_type: null,
  })
  const [historyUser, setHistoryUser] = useState<ProfileHistoryResponse['user'] | null>(null)

  const handleLogout = useCallback(async () => {
    const confirmed = window.confirm(
      'Are you sure you want to sign out? You will be redirected to the login page.'
    )

    if (!confirmed) return

    await logout()
    setIsProfilePanelOpen(false)
  }, [logout])

  const [uploadedStatements, setUploadedStatements] = useState<Array<{
    id: string
    name: string
    bank: string
    date: string
    status: 'Processed' | 'Pending' | 'Processing' | 'Failed'
  }>>([])

  const [generatedReports, setGeneratedReports] = useState<Array<{
    id: string
    name: string
    bank: string
    date: string
    downloadUrl: string
  }>>([])

  useEffect(() => {
    const savedData = localStorage.getItem('airco-form-data')
    if (savedData) {
      try {
        const parsed = JSON.parse(savedData)
        setUserDetails(parsed.userDetails || {
          fullName: '',
          accountType: '',
          bankName: '',
        })
        setMode(parsed.mode || 'free')
        setApiKey(parsed.apiKey || '')
        const restoredStep = parsed.step || 1
        setStep(restoredStep === 4 ? 3 : restoredStep)
      } catch (e) {
        console.error('Failed to load saved form data:', e)
      }
    }
  }, [])

  useEffect(() => {
    const dataToSave = {
      userDetails,
      mode,
      apiKey,
      step,
      timestamp: Date.now(),
    }
    localStorage.setItem('airco-form-data', JSON.stringify(dataToSave))
  }, [userDetails, mode, apiKey, step])

  const loadProfileHistory = useCallback(async () => {
    const token = await getValidSessionAccessToken()
    if (!token) return

    try {
      const headers: Record<string, string> = { Authorization: `Bearer ${token}` }
      Object.assign(headers, buildUserHeadersFromToken(token))
      const response = await fetch(`${APP_API_BASE}/profile/history`, {
        headers,
      })
      const data = await response.json().catch(() => null)
      if (!response.ok || !data) {
        return
      }

      setHistoryUser(data.user)
      setHistorySummary(data.summary)
      setUploadedStatements(
        (data.uploads || []).map((item: any) => ({
          id: item.job_id,
          name: item.name,
          bank: item.bank_name || 'Unknown',
          date: item.created_at ? new Date(item.created_at).toISOString().split('T')[0] : '',
          status:
            item.status === 'completed'
              ? 'Processed'
              : item.status === 'running'
                ? 'Processing'
                : item.status === 'failed'
                  ? 'Failed'
                  : 'Pending',
        }))
      )
      setGeneratedReports(
        (data.reports || []).map((item: any) => ({
          id: item.job_id,
          name: item.name,
          bank: item.bank_name || 'Unknown',
          date: item.created_at ? new Date(item.created_at).toISOString().split('T')[0] : '',
          downloadUrl: `/api/jobs/${item.job_id}/download`,
        }))
      )
    } catch (fetchError) {
      console.error('Failed to load profile history:', fetchError)
    }
  }, [])

  useEffect(() => {
    loadProfileHistory()
  }, [loadProfileHistory])

  const handleUserDetails = (details: UserDetails) => {
    setUserDetails(details)
    setStep(2)
  }

  const handleFileSelected = (selectedFile: File, password?: string) => {
    setFile(selectedFile)
    setPdfPassword(password)
    setStep(3)
  }

  const handleProcessingComplete = useCallback((data: ProcessingResult) => {
    const uploadDate = new Date().toISOString().split('T')[0]

    setResult(data)
    setJobId(null)
    setStep(5)
    setIsProcessing(false)

    setUploadedStatements(prev =>
      prev.map((f) => (f.status === 'Processing' ? { ...f, status: 'Processed' } : f))
    )

    if (data.excel_url && file) {
      const reportName = file.name.replace(/\.pdf$/i, '_Report.xlsx')
      setGeneratedReports(prev => [...prev, {
        id: `${Date.now()}_report`,
        name: reportName,
        bank: userDetails.bankName || 'Unknown',
        date: uploadDate,
        downloadUrl: data.excel_url,
      }])
    }
    loadProfileHistory()
  }, [file, userDetails.bankName, loadProfileHistory])

  const handleProcessingError = useCallback((message: string) => {
    setError(message)
    setJobId(null)
    setIsProcessing(false)
    setUploadedStatements(prev =>
      prev.map((f) => (f.status === 'Processing' ? { ...f, status: 'Failed' } : f))
    )
    setStep(3)
    loadProfileHistory()
  }, [loadProfileHistory])

  const handleModeSelect = async (selectedMode: ProcessingMode, key?: string) => {
    if (!file) return

    setMode(selectedMode)
    if (key) setApiKey(key)
    setIsProcessing(true)
    setError(null)

    const uploadId = Date.now().toString()
    const uploadDate = new Date().toISOString().split('T')[0]

    setUploadedStatements(prev => [...prev, {
      id: uploadId,
      name: file.name,
      bank: userDetails.bankName || 'Unknown',
      date: uploadDate,
      status: 'Processing',
    }])

    try {
      const data = await uploadStatement(file, userDetails, selectedMode, key, pdfPassword)
      setJobId(data.job_id)
      setStep(4)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Something went wrong. Please try again.')
      setUploadedStatements(prev =>
        prev.map((f) => (f.id === uploadId ? { ...f, status: 'Failed' } : f))
      )
      setStep(3)
      setIsProcessing(false)
    }
  }

  const handleBack = () => {
    if (step === 2) setStep(1)
    else if (step === 3) setStep(2)
    else if (step === 5) setStep(3)
  }

  const handleReset = () => {
    setStep(1)
    setUserDetails({ fullName: '', accountType: '', bankName: '' })
    setFile(null)
    setPdfPassword(undefined)
    setMode('free')
    setApiKey('')
    setJobId(null)
    setResult(null)
    setError(null)
    setIsProcessing(false)
    localStorage.removeItem('airco-form-data')
  }

  useEffect(() => {
    const handleEsc = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setIsProfilePanelOpen(false)
    }
    if (isProfilePanelOpen) {
      document.addEventListener('keydown', handleEsc)
      return () => document.removeEventListener('keydown', handleEsc)
    }
  }, [isProfilePanelOpen])

  useEffect(() => {
    if (step === 4 && !jobId && !isProcessing) {
      setStep(3)
    }
  }, [step, jobId, isProcessing])

  const stepLabels = ['Details', 'Upload', 'Mode', 'Processing', 'Report']
  const effectiveUser = historyUser || user
  const profileName =
    effectiveUser?.name
    || [effectiveUser?.given_name, effectiveUser?.family_name].filter(Boolean).join(' ')
    || userDetails.fullName.trim()
    || 'Your Workspace'
  const profileEmail = effectiveUser?.email || 'No email available'
  const accountTypeLabel = historySummary.latest_account_type
    || (userDetails.accountType
      ? userDetails.accountType.charAt(0).toUpperCase() + userDetails.accountType.slice(1)
      : 'Not set')

  return (
    <main className="min-h-screen bg-white">
      <div className="mx-auto max-w-[1440px] px-4 pb-10 pt-6 sm:px-6 lg:px-8">
        <Header onProfileClick={() => setIsProfilePanelOpen(true)} />

        <div className="max-w-3xl mx-auto">
          <section>
            <div className="mb-8 flex items-center justify-center gap-1.5">
              {[1, 2, 3, 4, 5].map((s) => (
                <div key={s} className="flex items-center gap-1.5">
                  <div className="flex flex-col items-center">
                    <div
                      className={`h-1 w-10 rounded-full transition-colors ${
                        s <= step ? 'bg-black' : 'bg-neutral-200'
                      }`}
                    />
                    <span
                      className={`mt-1 text-[9px] ${
                        s <= step ? 'text-neutral-600' : 'text-neutral-300'
                      }`}
                    >
                      {stepLabels[s - 1]}
                    </span>
                  </div>
                </div>
              ))}
            </div>

            <div className="rounded-2xl border border-border p-6 shadow-sm sm:p-8 lg:p-10">
              {error && step !== 4 && (
                <div className="mb-6 rounded-md border border-red-200 bg-red-50 px-4 py-3">
                  <p className="text-sm text-red-700">{error}</p>
                </div>
              )}

              {step === 1 && <StepForm onSubmit={handleUserDetails} initialDetails={userDetails} />}
              {step === 2 && <UploadStep onUpload={handleFileSelected} isProcessing={false} />}
              {step === 3 && <ModeSelection onSelect={handleModeSelect} isProcessing={isProcessing} />}
              {step === 4 && jobId && (
                <ProcessingStep
                  jobId={jobId}
                  mode={mode}
                  onComplete={handleProcessingComplete}
                  onError={handleProcessingError}
                />
              )}
              {step === 5 && result && <ResultStep result={result} />}

              {step !== 4 && (
                <div className="mt-6 flex items-center justify-between border-t border-neutral-100 pt-4">
                  {step > 1 ? (
                    <button
                      onClick={handleBack}
                      className="flex items-center gap-1 text-sm text-neutral-500 transition-colors hover:text-black"
                    >
                      <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="m15 18-6-6 6-6"/></svg>
                      Back
                    </button>
                  ) : <div />}
                  {step === 5 ? (
                    <button
                      onClick={handleReset}
                      className="flex items-center gap-1 rounded-md bg-black px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-neutral-800"
                    >
                      New Statement
                      <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="m9 18 6-6-6-6"/></svg>
                    </button>
                  ) : <div />}
                </div>
              )}
            </div>

            <footer className="mt-12 space-y-3 text-center">
              <p className="text-xs font-medium text-neutral-400">
                Airco Insights - Financial Categorization Engine
              </p>
              <p className="mx-auto max-w-lg text-[11px] leading-relaxed text-neutral-400">
                Upload your bank statement PDF and get a fully categorized, structured Excel report -
                with monthly summaries, category breakdowns, recurring transaction detection, and weekly analysis.
                No data is stored. Processing happens in real time.
              </p>

              <div className="flex flex-wrap items-center justify-center gap-2 pt-1">
                {BANKS.map(({ name, available }) => (
                  <span
                    key={name}
                    className={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[10px] ${
                      available
                        ? 'border-neutral-200 bg-neutral-50 text-neutral-500'
                        : 'border-dashed border-neutral-200 bg-white text-neutral-300'
                    }`}
                  >
                    <span className={`h-1.5 w-1.5 rounded-full ${available ? 'bg-green-400' : 'bg-neutral-300'}`} />
                    {name}
                    {!available && <span className="ml-0.5 text-[9px] text-neutral-300">soon</span>}
                  </span>
                ))}
              </div>

              <p className="mx-auto max-w-md text-[10px] leading-relaxed text-neutral-300">
                Airco Insights does not provide financial advice, predictions, or recommendations.
                The system only categorizes and structures transaction data.
              </p>
            </footer>
          </section>
        </div>
      </div>

      {isProfilePanelOpen && (
        <>
          <div
            className="fixed inset-0 bg-black/20 z-40 transition-opacity"
            onClick={() => setIsProfilePanelOpen(false)}
          />

          <div className="fixed top-0 right-0 h-full w-[420px] bg-white shadow-2xl z-50 transform transition-transform duration-300 ease-in-out translate-x-0">
            <div className="h-full overflow-y-auto">
              <div className="sticky top-0 bg-white border-b border-neutral-100 p-4 z-10">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <h2 className="text-lg font-semibold text-black">Profile</h2>
                  </div>
                  <div className="flex items-center gap-2">
                    <button className="inline-flex items-center gap-2 rounded-full border border-neutral-200 bg-white px-4 py-2 text-sm font-medium text-neutral-700 transition hover:border-neutral-300 hover:bg-neutral-50 shadow-sm">
                      <UserCircle2 className="h-4 w-4" />
                      Profile
                    </button>
                    <button
                      onClick={() => setIsProfilePanelOpen(false)}
                      className="rounded-full p-2 text-neutral-400 hover:bg-neutral-100 hover:text-neutral-600 transition"
                    >
                      <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="m18 6-12 12"/><path d="m6 6 12 12"/></svg>
                    </button>
                  </div>
                </div>
              </div>

              <div className="p-4 space-y-6 overflow-y-auto" style={{ maxHeight: 'calc(100vh - 80px)' }}>
                <div className="rounded-2xl border border-neutral-100 bg-neutral-50/80 p-4 shadow-sm">
                  <div className="flex items-center gap-4">
                    <div className="flex h-14 w-14 items-center justify-center rounded-full bg-white text-neutral-400 shadow-sm ring-1 ring-neutral-200">
                      <UserCircle2 className="h-8 w-8" />
                    </div>
                    <div className="flex-1">
                      <p className="text-base font-semibold text-black">{profileName}</p>
                      <p className="text-sm text-neutral-500">{profileEmail}</p>
                    </div>
                  </div>

                  <div className="mt-6 space-y-3">
                    <div className="flex items-center justify-between rounded-xl bg-white px-4 py-3 shadow-sm ring-1 ring-neutral-100">
                      <span className="text-sm text-neutral-600">Account Type</span>
                      <span className="text-sm font-medium text-black">{accountTypeLabel}</span>
                    </div>
                    <div className="grid grid-cols-3 gap-2">
                      <div className="rounded-xl bg-white px-3 py-3 text-center shadow-sm ring-1 ring-neutral-100">
                        <p className="text-lg font-semibold text-black">{historySummary.total_uploads}</p>
                        <p className="text-[11px] text-neutral-500">Uploads</p>
                      </div>
                      <div className="rounded-xl bg-white px-3 py-3 text-center shadow-sm ring-1 ring-neutral-100">
                        <p className="text-lg font-semibold text-black">{historySummary.processed_files}</p>
                        <p className="text-[11px] text-neutral-500">Processed</p>
                      </div>
                      <div className="rounded-xl bg-white px-3 py-3 text-center shadow-sm ring-1 ring-neutral-100">
                        <p className="text-lg font-semibold text-black">{historySummary.generated_reports}</p>
                        <p className="text-[11px] text-neutral-500">Reports</p>
                      </div>
                    </div>
                    <button
                      onClick={handleLogout}
                      className="w-full rounded-lg bg-red-50 px-4 py-2 text-sm font-medium text-red-600 transition hover:bg-red-100"
                    >
                      Sign Out
                    </button>
                  </div>
                </div>

                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <h3 className="text-base font-semibold text-black">Files</h3>
                    <div className="inline-flex rounded-full bg-neutral-100 p-0.5 text-xs font-medium text-neutral-500">
                      <button
                        type="button"
                        onClick={() => { setFilesTab('uploaded'); setSelectedFiles(new Set()) }}
                        className={`rounded-full px-3 py-1 transition ${filesTab === 'uploaded' ? 'bg-white text-black shadow-sm' : ''}`}
                      >
                        Uploaded Statements
                      </button>
                      <button
                        type="button"
                        onClick={() => { setFilesTab('reports'); setSelectedFiles(new Set()) }}
                        className={`rounded-full px-3 py-1 transition ${filesTab === 'reports' ? 'bg-white text-black shadow-sm' : ''}`}
                      >
                        Generated Reports
                      </button>
                    </div>
                  </div>

                  {selectedFiles.size > 0 && (
                    <div className="flex items-center justify-between rounded-lg bg-neutral-50 px-3 py-2">
                      <span className="text-sm text-neutral-600">{selectedFiles.size} selected</span>
                      <button
                        onClick={() => {
                          setSelectedFiles(new Set())
                        }}
                        className="text-sm text-red-600 hover:text-red-700 transition"
                      >
                        Delete
                      </button>
                    </div>
                  )}

                  <div className="space-y-1">
                    {filesTab === 'uploaded' ? (
                      uploadedStatements.length > 0 ? (
                        uploadedStatements.map((item) => (
                          <div
                            key={item.id}
                            className="group flex items-center gap-3 rounded-lg px-3 py-2 transition hover:bg-neutral-50"
                          >
                            <input
                              type="checkbox"
                              checked={selectedFiles.has(item.id)}
                              onChange={(e) => {
                                const newSelected = new Set(selectedFiles)
                                if (e.target.checked) {
                                  newSelected.add(item.id)
                                } else {
                                  newSelected.delete(item.id)
                                }
                                setSelectedFiles(newSelected)
                              }}
                              className="h-4 w-4 rounded border-neutral-300 text-black focus:ring-black"
                            />
                            <div className="flex h-8 w-8 items-center justify-center rounded bg-red-50 text-red-500">
                              <FileText className="h-4 w-4" />
                            </div>
                            <div className="flex-1 min-w-0">
                              <p className="truncate text-sm font-medium text-black">{item.name}</p>
                              <p className="text-xs text-neutral-500">{item.date}</p>
                            </div>
                            <div className={`h-2 w-2 rounded-full ${
                              item.status === 'Processed' ? 'bg-green-500' :
                              item.status === 'Processing' ? 'bg-yellow-500' :
                              item.status === 'Failed' ? 'bg-red-500' :
                              'bg-neutral-300'
                            }`} />
                            <div className="opacity-0 group-hover:opacity-100 transition flex items-center gap-1">
                              <button
                                onClick={() => setUploadedStatements(prev => prev.filter((f) => f.id !== item.id))}
                                className="p-1 rounded text-neutral-400 hover:text-red-600 transition"
                              >
                                <Trash2 className="h-4 w-4" />
                              </button>
                            </div>
                          </div>
                        ))
                      ) : (
                        <div className="flex flex-col items-center justify-center py-8 text-center">
                          <FileText className="h-8 w-8 text-neutral-300" />
                          <p className="mt-2 text-sm text-neutral-500">No files yet</p>
                        </div>
                      )
                    ) : (
                      generatedReports.length > 0 ? (
                        generatedReports.map((item) => (
                          <div
                            key={item.id}
                            className="group flex items-center gap-3 rounded-lg px-3 py-2 transition hover:bg-neutral-50"
                          >
                            <input
                              type="checkbox"
                              checked={selectedFiles.has(item.id)}
                              onChange={(e) => {
                                const newSelected = new Set(selectedFiles)
                                if (e.target.checked) {
                                  newSelected.add(item.id)
                                } else {
                                  newSelected.delete(item.id)
                                }
                                setSelectedFiles(newSelected)
                              }}
                              className="h-4 w-4 rounded border-neutral-300 text-black focus:ring-black"
                            />
                            <div className="flex h-8 w-8 items-center justify-center rounded bg-green-50 text-green-600">
                              <FileSpreadsheet className="h-4 w-4" />
                            </div>
                            <div className="flex-1 min-w-0">
                              <p className="truncate text-sm font-medium text-black">{item.name}</p>
                              <p className="text-xs text-neutral-500">{item.date}</p>
                            </div>
                            <div className="opacity-0 group-hover:opacity-100 transition flex items-center gap-1">
                              <a
                                href={item.downloadUrl}
                                download
                                className="p-1 rounded text-neutral-400 hover:text-black transition"
                              >
                                <Download className="h-4 w-4" />
                              </a>
                              <button
                                onClick={() => setGeneratedReports(prev => prev.filter((r) => r.id !== item.id))}
                                className="p-1 rounded text-neutral-400 hover:text-red-600 transition"
                              >
                                <Trash2 className="h-4 w-4" />
                              </button>
                            </div>
                          </div>
                        ))
                      ) : (
                        <div className="flex flex-col items-center justify-center py-8 text-center">
                          <FileSpreadsheet className="h-8 w-8 text-neutral-300" />
                          <p className="mt-2 text-sm text-neutral-500">No files yet</p>
                        </div>
                      )
                    )}
                  </div>
                </div>
              </div>
            </div>
          </div>
        </>
      )}
    </main>
  )
}

async function uploadStatement(
  file: File,
  userDetails: UserDetails,
  mode: ProcessingMode,
  apiKey?: string,
  pdfPassword?: string,
): Promise<JobSubmitted> {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('full_name', userDetails.fullName || '')
  formData.append('account_type', userDetails.accountType || '')
  formData.append('bank_name', userDetails.bankName || '')
  formData.append('mode', mode)
  if (apiKey) formData.append('api_key', apiKey)
  if (pdfPassword) formData.append('pdf_password', pdfPassword)

  const token = await getValidSessionAccessToken()
  const headers: Record<string, string> | undefined = token
    ? { Authorization: `Bearer ${token}`, ...buildUserHeadersFromToken(token) }
    : undefined
  const resp = await fetch(`${APP_API_BASE}/upload`, {
    method: 'POST',
    body: formData,
    headers,
  })
  const data = await resp.json().catch(() => ({}))
  if (!resp.ok) {
    throw new Error(data.message || 'Upload failed. Please try again.')
  }
  return data as JobSubmitted
}
