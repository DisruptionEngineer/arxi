"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { ingestNewRx } from "@/lib/api";

const SAMPLE_XML = `<?xml version="1.0" encoding="UTF-8"?>
<Message>
  <Header>
    <MessageID>MSG-2026-00042</MessageID>
    <SentTime>2026-03-13T14:30:00Z</SentTime>
    <From>
      <Qualifier>D</Qualifier>
      <Value>EMR-SYSTEM-001</Value>
    </From>
    <To>
      <Qualifier>P</Qualifier>
      <Value>PHARMAGENT-001</Value>
    </To>
  </Header>
  <Body>
    <NewRx>
      <Patient>
        <HumanPatient>
          <Name>
            <FirstName>Sarah</FirstName>
            <LastName>Williams</LastName>
          </Name>
          <Gender>F</Gender>
          <DateOfBirth>
            <Date>1985-07-22</Date>
          </DateOfBirth>
          <Address>
            <AddressLine1>742 Evergreen Terrace</AddressLine1>
            <City>Springfield</City>
            <StateProvince>IL</StateProvince>
            <PostalCode>62704</PostalCode>
          </Address>
        </HumanPatient>
      </Patient>
      <Prescriber>
        <NonVeterinarian>
          <Name>
            <FirstName>James</FirstName>
            <LastName>Wilson</LastName>
          </Name>
          <Identification>
            <NPI>1003000126</NPI>
            <DEANumber>AW1234567</DEANumber>
          </Identification>
        </NonVeterinarian>
      </Prescriber>
      <MedicationPrescribed>
        <DrugDescription>Amoxicillin 500mg Capsules</DrugDescription>
        <DrugCoded>
          <ProductCode>
            <Code>00093-3109-01</Code>
          </ProductCode>
        </DrugCoded>
        <Quantity>
          <Value>30</Value>
        </Quantity>
        <DaysSupply>10</DaysSupply>
        <NumberOfRefills>0</NumberOfRefills>
        <Sig>
          <SigText>Take 1 capsule by mouth 3 times daily for 10 days</SigText>
        </Sig>
        <WrittenDate>
          <Date>2026-03-13</Date>
        </WrittenDate>
        <Substitutions>0</Substitutions>
      </MedicationPrescribed>
    </NewRx>
  </Body>
</Message>`;

export default function IngestPage() {
  const router = useRouter();
  const [xml, setXml] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<{
    id: string;
    status: string;
    patient: string;
    drug: string;
  } | null>(null);

  const handleSubmit = async () => {
    if (!xml.trim()) return;
    setSubmitting(true);
    setError(null);
    setResult(null);
    try {
      const rx = await ingestNewRx(xml);
      setResult({
        id: rx.id,
        status: rx.status,
        patient: `${rx.patient_last_name}, ${rx.patient_first_name}`,
        drug: rx.drug_description,
      });
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Ingest failed");
    } finally {
      setSubmitting(false);
    }
  };

  const loadSample = () => {
    setXml(SAMPLE_XML);
    setError(null);
    setResult(null);
  };

  return (
    <div className="max-w-4xl">
      <div className="flex items-center gap-3 mb-6">
        <button
          onClick={() => router.push("/queue")}
          className="text-gray-400 hover:text-white text-sm"
        >
          &larr; Queue
        </button>
        <h1 className="text-xl font-semibold">E-Prescribe Ingest</h1>
        <span className="text-xs text-gray-500 bg-purple-900/40 text-purple-300 px-2 py-0.5 rounded-full">
          NCPDP SCRIPT
        </span>
      </div>

      <p className="text-sm text-gray-400 mb-4">
        Paste NCPDP SCRIPT NewRx XML to ingest an e-prescription. The Rx will enter the pipeline
        as <span className="text-cyan-400 font-mono text-xs">PARSED</span> and automatically
        advance through validation, patient matching, and review.
      </p>

      {/* XML Input */}
      <div className="mb-4">
        <div className="flex items-center justify-between mb-2">
          <label className="text-xs text-gray-400 uppercase tracking-wider">
            NCPDP SCRIPT XML
          </label>
          <button
            onClick={loadSample}
            className="text-xs text-blue-400 hover:text-blue-300"
          >
            Load Sample
          </button>
        </div>
        <textarea
          className="w-full bg-gray-900 border border-gray-700 rounded-lg px-4 py-3 text-sm text-gray-100 font-mono placeholder:text-gray-600 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 resize-y"
          rows={18}
          value={xml}
          onChange={(e) => {
            setXml(e.target.value);
            setResult(null);
          }}
          placeholder="<?xml version=&quot;1.0&quot;?>\n<Message>\n  <Header>...</Header>\n  <Body>\n    <NewRx>...</NewRx>\n  </Body>\n</Message>"
          spellCheck={false}
        />
      </div>

      {/* Error */}
      {error && (
        <div className="bg-red-900/30 border border-red-700 rounded-lg p-3 text-red-300 text-sm mb-4">
          {error}
        </div>
      )}

      {/* Success */}
      {result && (
        <div className="bg-green-900/20 border border-green-700/50 rounded-lg p-4 mb-4">
          <div className="flex items-center gap-2 mb-2">
            <span className="text-green-400 text-sm font-medium">Rx Ingested Successfully</span>
            <span className="text-xs bg-cyan-900/40 text-cyan-300 px-2 py-0.5 rounded-full font-mono">
              {result.status}
            </span>
          </div>
          <div className="grid grid-cols-3 gap-4 text-sm">
            <div>
              <span className="text-[11px] text-gray-500 uppercase tracking-wider">Patient</span>
              <p className="text-gray-200 mt-0.5">{result.patient}</p>
            </div>
            <div>
              <span className="text-[11px] text-gray-500 uppercase tracking-wider">Drug</span>
              <p className="text-gray-200 mt-0.5">{result.drug}</p>
            </div>
            <div>
              <span className="text-[11px] text-gray-500 uppercase tracking-wider">Rx ID</span>
              <p className="text-gray-200 font-mono mt-0.5">{result.id.slice(0, 8)}</p>
            </div>
          </div>
          <div className="flex gap-3 mt-3">
            <button
              onClick={() => router.push(`/review/${result.id}`)}
              className="text-xs text-blue-400 hover:text-blue-300"
            >
              View in Review &rarr;
            </button>
            <button
              onClick={() => router.push("/queue")}
              className="text-xs text-gray-400 hover:text-gray-200"
            >
              Back to Queue
            </button>
          </div>
          <p className="text-[11px] text-gray-600 mt-2">
            The worker pipeline will advance this Rx: PARSED &rarr; VALIDATED &rarr; PENDING_REVIEW
          </p>
        </div>
      )}

      {/* Actions */}
      <div className="flex gap-3">
        <button
          onClick={handleSubmit}
          disabled={!xml.trim() || submitting}
          className="px-5 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-md text-sm font-medium disabled:opacity-40 disabled:cursor-not-allowed"
        >
          {submitting ? "Ingesting..." : "Ingest Rx"}
        </button>
        <button
          onClick={() => {
            setXml("");
            setError(null);
            setResult(null);
          }}
          className="px-4 py-2 bg-gray-800 hover:bg-gray-700 text-gray-300 rounded-md text-sm"
        >
          Clear
        </button>
      </div>
    </div>
  );
}
