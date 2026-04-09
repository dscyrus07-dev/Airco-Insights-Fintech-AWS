'use client'

import Image from 'next/image'
import { UserCircle2 } from 'lucide-react'

interface HeaderProps {
  onProfileClick?: () => void
}

export default function Header({ onProfileClick }: HeaderProps) {
  return (
    <header className="w-full pt-10 pb-6 text-center">
      <div className="flex items-center justify-between mb-2 max-w-[1440px] mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-center gap-3 flex-1">
          <Image
            src="/logo.png"
            alt="Airco Insights"
            width={36}
            height={36}
            className="rounded"
          />
          <h1 className="text-2xl font-semibold tracking-tight text-black">
            Airco Insights
          </h1>
        </div>
        <button
          onClick={onProfileClick}
          className="flex items-center gap-2 rounded-full border border-neutral-200 bg-white px-4 py-2 text-sm font-medium text-neutral-700 transition hover:border-neutral-300 hover:bg-neutral-50 shadow-sm"
        >
          <UserCircle2 className="h-5 w-5" />
          Profile
        </button>
      </div>
      <div className="max-w-[1440px] mx-auto px-4 sm:px-6 lg:px-8">
        <p className="text-sm text-neutral-500 tracking-wide">
          Financial Categorization Engine
        </p>
      </div>
    </header>
  )
}
