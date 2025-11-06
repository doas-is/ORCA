import { Download, FileJson, FileSpreadsheet, FileText } from "lucide-react";
import { Button } from "@/components/ui/button";

const ExportReport = () => {
  return (
    <div className="ocean-gradient min-h-screen pt-24 pb-16">
      <div className="container mx-auto px-4 sm:px-6 lg:px-8 max-w-5xl">
        <div className="text-center mb-12 animate-fade-in">
          <div className="flex items-center justify-center space-x-3 mb-4">
            <Download className="w-12 h-12 text-logo" />
            <h1 className="text-4xl font-bold text-foreground">ORCA</h1>
          </div>
          <h2 className="text-3xl font-bold text-foreground mb-4">Export Report</h2>
          <p className="text-xl text-foreground-secondary">
            Download your competitive analysis in multiple formats
          </p>
        </div>

        <div className="glass-card rounded-2xl p-8 mb-8 animate-fade-in">
          <h3 className="text-2xl font-bold text-foreground mb-6">Report Summary</h3>
          
          <div className="grid gap-4 md:grid-cols-2 mb-8">
            {[
              { label: "Total Competitors Analyzed", value: "5" },
              { label: "Content Opportunities Found", value: "47" },
              { label: "Keywords Analyzed", value: "382" },
              { label: "Articles Crawled", value: "181" },
            ].map((stat, i) => (
              <div key={i} className="p-4 bg-secondary/30 rounded-lg">
                <div className="text-2xl font-bold text-kelp mb-1">{stat.value}</div>
                <div className="text-sm text-foreground-secondary">{stat.label}</div>
              </div>
            ))}
          </div>

          <div className="space-y-4">
            <h4 className="font-semibold text-foreground">Choose Export Format:</h4>
            
            {[
              { icon: FileJson, label: "JSON", description: "Machine-readable format for API integration", color: "text-white dark:text-kelp" },
              { icon: FileSpreadsheet, label: "CSV/Excel", description: "Spreadsheet format for data analysis", color: "text-white dark:text-kelp" },
              { icon: FileText, label: "PDF Report", description: "Executive summary with visualizations", color: "text-white dark:text-kelp" },
            ].map((format, i) => (
              <div
                key={i}
                className="glass-card rounded-xl p-6 flex items-center justify-between hover-lift"
                style={{ animationDelay: `${i * 100}ms` }}
              >
                <div className="flex items-center gap-4">
                  <div className="w-12 h-12 rounded-full bg-secondary flex items-center justify-center">
                    <format.icon className={`w-6 h-6 ${format.color}`} />
                  </div>
                  <div>
                    <h5 className="font-bold text-foreground">{format.label}</h5>
                    <p className="text-sm text-foreground-secondary">{format.description}</p>
                  </div>
                </div>
                <Button className="bg-primary hover:bg-primary/90 text-primary-foreground">
                  <Download className="w-4 h-4 mr-2" />
                  Download
                </Button>
              </div>
            ))}
          </div>
        </div>

        <div className="glass-card rounded-2xl p-8 animate-fade-in-up text-center">
          <h3 className="text-xl font-bold text-foreground mb-4">Need API Access?</h3>
          <p className="text-foreground-secondary mb-6">
            Integrate ORCA's competitive intelligence directly into your tools and workflows
          </p>
          <Button variant="outline" size="lg">
            View API Documentation →
          </Button>
        </div>
      </div>
    </div>
  );
};

export default ExportReport;
