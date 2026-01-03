'use client';

import { useState, useEffect, useRef } from 'react';

interface SearchInputProps {
    onSearch: (query: string) => void;
    placeholder?: string;
    initialValue?: string;
}

export default function SearchInput({
    onSearch,
    placeholder = "Search by fund name or ticker...",
    initialValue = ""
}: SearchInputProps) {
    const [value, setValue] = useState(initialValue);
    const debounceTimer = useRef<NodeJS.Timeout | null>(null);

    // Sync internal state with prop when it changes from parent (e.g., after search completes)
    useEffect(() => {
        // #region agent log
        fetch('http://127.0.0.1:7242/ingest/7f418701-bce6-449b-9ec6-0178fb2b8930',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'SearchInput.tsx:useEffect-initialValue',message:'initialValue prop changed',data:{initialValue,currentValue:value,valuesMatch:initialValue===value},timestamp:Date.now(),sessionId:'debug-session',runId:'post-fix',hypothesisId:'A'})}).catch(()=>{});
        // #endregion
        if (initialValue !== value) {
            setValue(initialValue);
        }
    }, [initialValue]); // Only depend on initialValue, not value, to avoid loops

    // Handle input change
    const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        const newValue = e.target.value;
        // #region agent log
        fetch('http://127.0.0.1:7242/ingest/7f418701-bce6-449b-9ec6-0178fb2b8930',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'SearchInput.tsx:handleChange',message:'Input changed',data:{newValue,oldValue:value,hasDebounceTimer:!!debounceTimer.current},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'A,C'})}).catch(()=>{});
        // #endregion
        setValue(newValue);

        // Debounce search
        if (debounceTimer.current) {
            clearTimeout(debounceTimer.current);
        }

        debounceTimer.current = setTimeout(() => {
            // #region agent log
            fetch('http://127.0.0.1:7242/ingest/7f418701-bce6-449b-9ec6-0178fb2b8930',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'SearchInput.tsx:debounced-onSearch',message:'Calling onSearch after debounce',data:{newValue},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'B'})}).catch(()=>{});
            // #endregion
            onSearch(newValue);
        }, 300);
    };

    // Handle clear
    const handleClear = () => {
        setValue("");
        onSearch("");
        if (debounceTimer.current) {
            clearTimeout(debounceTimer.current);
        }
    };

    // Cleanup
    useEffect(() => {
        return () => {
            if (debounceTimer.current) {
                clearTimeout(debounceTimer.current);
            }
        };
    }, []);

    return (
        <div className="relative mb-6">
            <div className="absolute inset-y-0 left-0 flex items-center pl-3 pointer-events-none">
                <svg
                    className="w-4 h-4 text-gray-400"
                    aria-hidden="true"
                    xmlns="http://www.w3.org/2000/svg"
                    fill="none"
                    viewBox="0 0 20 20"
                >
                    <path
                        stroke="currentColor"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth="2"
                        d="m19 19-4-4m0-7A7 7 0 1 1 1 8a7 7 0 0 1 14 0Z"
                    />
                </svg>
            </div>

            <input
                type="text"
                className="block w-full p-4 pl-10 text-sm border border-brand-light rounded-lg bg-gray-50 focus:ring-brand-primary focus:border-brand-primary placeholder-gray-400 text-gray-900 shadow-sm"
                placeholder={placeholder}
                value={value}
                onChange={handleChange}
            />

            {value && (
                <button
                    onClick={handleClear}
                    className="absolute inset-y-0 right-0 flex items-center pr-3 text-gray-500 hover:text-gray-900"
                    type="button"
                >
                    <svg
                        className="w-4 h-4"
                        xmlns="http://www.w3.org/2000/svg"
                        fill="none"
                        viewBox="0 0 24 24"
                        stroke="currentColor"
                    >
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                    </svg>
                </button>
            )}
        </div>
    );
}
