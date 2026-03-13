"use client";
import { useCallback, useRef, useState } from "react";
import { validateNPI } from "@/lib/api";
import type { NPIValidationResult } from "@/lib/types";

interface Props {
  value: string;
  onChange: (value: string) => void;
  onPrescriberFound?: (name: string) => void;
  className?: string;
}

export function NPIField({ value, onChange, onPrescriberFound, className }: Props) {
  const [validation, setValidation] = useState<NPIValidationResult | null>(null);
  const [loading, setLoading] = useState(false);
  const timerRef = useRef<ReturnType<typeof setTimeout>>(undefined);

  const doValidate = useCallback(async (npi: string) => {
    const cleaned = npi.replace(/\D/g, "");
    if (cleaned.length !== 10) {
      setValidation(null);
      return;
    }
    setLoading(true);
    try {
      const result = await validateNPI(cleaned);
      setValidation(result);
      if (result.found && result.name && onPrescriberFound) {
        onPrescriberFound(result.name);
      }
    } catch {
      setValidation(null);
    } finally {
      setLoading(false);
    }
  }, [onPrescriberFound]);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = e.target.value;
    onChange(val);
    setValidation(null);
    clearTimeout(timerRef.current);
    // Auto-validate when 10 digits entered
    const cleaned = val.replace(/\D/g, "");
    if (cleaned.length === 10) {
      timerRef.current = setTimeout(() => doValidate(val), 300);
    }
  };

  const handleBlur = () => {
    const cleaned = value.replace(/\D/g, "");
    if (cleaned.length === 10 && !validation) {
      doValidate(value);
    }
  };

  return (
    <div>
      <div className="relative">
        <input
          type="text"
          value={value}
          onChange={handleChange}
          onBlur={handleBlur}
          placeholder="1234567890"
          maxLength={10}
          className={className}
          autoComplete="off"
        />
        {loading && (
          <div className="absolute right-2 top-1/2 -translate-y-1/2">
            <div className="w-4 h-4 border-2 border-gray-600 border-t-blue-400 rounded-full animate-spin" />
          </div>
        )}
      </div>

      {/* Validation result badge */}
      {validation && (
        <div className="mt-1.5">
          {validation.valid && validation.found ? (
            <div className="bg-emerald-900/30 border border-emerald-800/50 rounded px-2 py-1.5">
              <div className="flex items-center gap-1.5">
                <span className="text-emerald-400 text-xs font-medium">Verified</span>
                <span className="text-[10px] text-gray-500">{validation.enumeration_type}</span>
              </div>
              <p className="text-xs text-gray-200 mt-0.5">
                {validation.name}
                {validation.credential && <span className="text-gray-500">, {validation.credential}</span>}
              </p>
              {validation.specialty && (
                <p className="text-[11px] text-gray-500">{validation.specialty}</p>
              )}
              {validation.address_city && (
                <p className="text-[11px] text-gray-600">
                  {validation.address_city}, {validation.address_state}
                </p>
              )}
            </div>
          ) : validation.valid && !validation.found ? (
            <div className="bg-yellow-900/30 border border-yellow-800/50 rounded px-2 py-1">
              <span className="text-yellow-400 text-xs">Valid format</span>
              <span className="text-[11px] text-gray-500 ml-1">Not found in NPPES</span>
            </div>
          ) : (
            <div className="bg-red-900/30 border border-red-800/50 rounded px-2 py-1">
              <span className="text-red-400 text-xs">{validation.message}</span>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
