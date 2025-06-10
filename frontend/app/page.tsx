"use client";

import { useState } from "react";
import { LabelAnalysisResult } from "@/lib/types";
import { submitLabelForAnalysis } from "@/lib/api";
import { toast } from "sonner";
import { Toaster } from "../components/ui/sonner";

// Import feature components
import { ImageUploader } from "../components/features/label-checker/ImageUploader";
import { RulesUploader } from "../components/features/label-checker/RulesUploader";
import { AnalysisResultDisplay } from "../components/features/label-checker/AnalysisResult";

// Import UI Primitives
import { Button } from "../components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "../components/ui/card";
import { Alert, AlertDescription, AlertTitle } from "../components/ui/alert";
import { Terminal } from "lucide-react";

export default function Home() {
  const [imageFile, setImageFile] = useState<File | null>(null);
  const [rulesFile, setRulesFile] = useState<File | null>(null); // <-- State for rules file
  const [imageUrl, setImageUrl] = useState<string | null>(null);

  // State for the API call
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [analysisResult, setAnalysisResult] =
    useState<LabelAnalysisResult | null>(null);

  const handleImageUpload = (file: File) => {
    setImageFile(file);
    if (imageUrl) URL.revokeObjectURL(imageUrl);
    setImageUrl(URL.createObjectURL(file));
  };

  const handleRulesUpload = (file: File) => {
    setRulesFile(file);
  };

  const handleSubmit = async () => {
    if (!imageFile || !rulesFile) {
      // Check for both files
      setError("Please provide both a label image and a rules document.");
      return;
    }

    setIsLoading(true);
    setError(null);
    setAnalysisResult(null);

    try {
      // The api function now expects a File object for the rules
      const result = await submitLabelForAnalysis(imageFile, rulesFile, 50);
      setAnalysisResult(result);
      toast.success("Analysis Complete", {
        description: `Overall status: ${result.overall_status
          .replace("_", " ")
          .toUpperCase()}`,
      });
    } catch (err) {
      const errorMessage =
        err instanceof Error ? err.message : "An unknown error occurred.";
      setError(errorMessage);
      toast.error("Analysis Failed", {
        description: errorMessage,
      });
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <main className="flex min-h-screen flex-col items-center p-4 md:p-12 lg:p-24 bg-gray-50 dark:bg-gray-900">
      <div className="w-full max-w-6xl space-y-8">
        <header className="text-center">
          <h1 className="text-4xl font-bold tracking-tight text-gray-900 dark:text-gray-50">
            AI Regulatory Label Checker
          </h1>
          <p className="mt-2 text-lg text-gray-600 dark:text-gray-300">
            Upload your label and rules document to get instant, precise
            compliance feedback.
          </p>
        </header>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* Input Section */}
          <Card>
            <CardHeader>
              <CardTitle>1. Upload Your Files</CardTitle>
              <CardDescription>
                Provide the label image and the rules document.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div>
                <label className="text-sm font-medium mb-2 block">
                  Label Image
                </label>
                <ImageUploader
                  onFileSelect={handleImageUpload}
                  currentImageUrl={imageUrl}
                />
              </div>
              <div>
                <label className="text-sm font-medium mb-2 block">
                  Rules Document
                </label>
                <RulesUploader
                  onFileSelect={handleRulesUpload}
                  currentFile={rulesFile}
                />
              </div>
              <Button
                onClick={handleSubmit}
                disabled={isLoading || !imageFile || !rulesFile}
                className="w-full"
              >
                {isLoading ? "Analyzing..." : "Analyze Label"}
              </Button>
            </CardContent>
          </Card>

          {/* Results Section */}
          <Card>
            <CardHeader>
              <CardTitle>2. Analysis Results</CardTitle>
              <CardDescription>
                Highlights will appear on your image below.
              </CardDescription>
            </CardHeader>
            <CardContent>
              {error && (
                <Alert variant="destructive">
                  <Terminal className="h-4 w-4" />
                  <AlertTitle>Error</AlertTitle>
                  <AlertDescription>{error}</AlertDescription>
                </Alert>
              )}
              <AnalysisResultDisplay
                imageUrl={imageUrl}
                result={analysisResult}
                isLoading={isLoading}
              />
            </CardContent>
          </Card>
        </div>
      </div>
      <Toaster />
    </main>
  );
}
