import { useState } from "react";
import { Link } from "wouter";
import { useListParcels } from "@workspace/api-client-react";
import { type ListParcelsParams, ParcelStatus, ParcelParcelType } from "@workspace/api-client-react";
import { AppLayout } from "@/components/layout/app-layout";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Button } from "@/components/ui/button";
import { StatusBadge } from "@/components/ui/status-badge";
import { TrustScoreGauge } from "@/components/ui/trust-score-gauge";
import { Map, Search, Filter, Plus } from "lucide-react";
import { format } from "date-fns";

const STATES = [
  "Lagos", "Abuja (FCT)", "Rivers", "Kano", "Ogun", "Oyo", 
  "Delta", "Edo", "Kaduna", "Anambra", "Enugu", "Imo", 
  "Cross River", "Akwa Ibom", "Plateau"
];

export function ParcelsRegistry() {
  const [params, setParams] = useState<ListParcelsParams>({
    limit: 50,
    offset: 0,
  });

  const [searchInput, setSearchInput] = useState("");

  const { data, isLoading } = useListParcels(params);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    setParams({ ...params, search: searchInput || undefined, offset: 0 });
  };

  const handleFilterChange = (key: keyof ListParcelsParams, value: string) => {
    if (value === "all") {
      const newParams = { ...params, offset: 0 };
      delete newParams[key];
      setParams(newParams);
    } else {
      setParams({ ...params, [key]: value, offset: 0 });
    }
  };

  return (
    <AppLayout>
      <div className="flex flex-col gap-6">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h1 className="text-3xl font-bold text-foreground">Land Registry</h1>
            <p className="text-muted-foreground mt-1 text-lg">Comprehensive database of registered parcels.</p>
          </div>
          <Link href="/parcels/new">
            <Button className="w-full sm:w-auto">
              <Plus className="mr-2 h-4 w-4" />
              Register Parcel
            </Button>
          </Link>
        </div>

        <Card className="p-4">
          <form onSubmit={handleSearch} className="flex flex-col md:flex-row gap-4">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                placeholder="Search by title number, owner name, or address..."
                className="pl-10"
                value={searchInput}
                onChange={(e) => setSearchInput(e.target.value)}
              />
            </div>
            <div className="flex gap-4">
              <Select value={params.status || "all"} onValueChange={(val) => handleFilterChange("status", val)}>
                <SelectTrigger className="w-[140px]">
                  <SelectValue placeholder="Status" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Statuses</SelectItem>
                  {Object.values(ParcelStatus).map(s => (
                    <SelectItem key={s} value={s}>{s.charAt(0).toUpperCase() + s.slice(1)}</SelectItem>
                  ))}
                </SelectContent>
              </Select>

              <Select value={params.parcel_type || "all"} onValueChange={(val) => handleFilterChange("parcel_type", val)}>
                <SelectTrigger className="w-[140px]">
                  <SelectValue placeholder="Type" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Types</SelectItem>
                  {Object.values(ParcelParcelType).map(t => (
                    <SelectItem key={t} value={t}>{t.charAt(0).toUpperCase() + t.slice(1)}</SelectItem>
                  ))}
                </SelectContent>
              </Select>

              <Select value={params.state || "all"} onValueChange={(val) => handleFilterChange("state", val)}>
                <SelectTrigger className="w-[140px]">
                  <SelectValue placeholder="State" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All States</SelectItem>
                  {STATES.map(s => (
                    <SelectItem key={s} value={s}>{s}</SelectItem>
                  ))}
                </SelectContent>
              </Select>

              <Button type="submit" variant="secondary" className="md:w-auto shrink-0">
                <Filter className="mr-2 h-4 w-4" />
                Apply
              </Button>
            </div>
          </form>
        </Card>

        <Card className="overflow-hidden border">
          <div className="overflow-x-auto">
            <table className="w-full text-sm text-left">
              <thead className="bg-muted/50 text-muted-foreground text-xs uppercase tracking-wider">
                <tr>
                  <th className="px-6 py-4 font-semibold">Title Number</th>
                  <th className="px-6 py-4 font-semibold">Owner & Location</th>
                  <th className="px-6 py-4 font-semibold">Details</th>
                  <th className="px-6 py-4 font-semibold text-center">Trust</th>
                  <th className="px-6 py-4 font-semibold text-right">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {isLoading ? (
                  [...Array(5)].map((_, i) => (
                    <tr key={i} className="animate-pulse">
                      <td className="px-6 py-4"><div className="h-4 w-24 bg-muted rounded" /></td>
                      <td className="px-6 py-4">
                        <div className="h-4 w-32 bg-muted rounded mb-2" />
                        <div className="h-3 w-48 bg-muted rounded" />
                      </td>
                      <td className="px-6 py-4"><div className="h-4 w-16 bg-muted rounded" /></td>
                      <td className="px-6 py-4"><div className="mx-auto h-8 w-8 bg-muted rounded-full" /></td>
                      <td className="px-6 py-4 text-right"><div className="h-6 w-20 bg-muted rounded ml-auto" /></td>
                    </tr>
                  ))
                ) : data && data.items.length > 0 ? (
                  data.items.map(parcel => (
                    <tr key={parcel.id} className="hover:bg-muted/30 transition-colors group cursor-pointer relative">
                      <td className="px-6 py-4">
                        <Link href={`/parcels/${parcel.id}`} className="absolute inset-0 z-10">
                          <span className="sr-only">View Parcel</span>
                        </Link>
                        <span className="font-semibold text-primary group-hover:underline">
                          {parcel.title_number}
                        </span>
                        <div className="text-xs text-muted-foreground mt-1">
                          Reg: {format(new Date(parcel.created_at), "MMM d, yyyy")}
                        </div>
                      </td>
                      <td className="px-6 py-4">
                        <div className="font-medium text-foreground">{parcel.owner_name}</div>
                        <div className="text-muted-foreground mt-1 flex items-center gap-1">
                          <Map className="h-3 w-3 inline" />
                          {parcel.lga}, {parcel.state}
                        </div>
                      </td>
                      <td className="px-6 py-4">
                        <div>{parcel.area_sqm.toLocaleString()} sqm</div>
                        <div className="text-muted-foreground capitalize mt-1">{parcel.parcel_type}</div>
                      </td>
                      <td className="px-6 py-2 text-center">
                        <TrustScoreGauge score={parcel.trust_score} size="sm" showLabel={false} className="mx-auto" />
                      </td>
                      <td className="px-6 py-4 text-right relative z-20">
                        <StatusBadge status={parcel.status} />
                      </td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan={5} className="px-6 py-12 text-center">
                      <div className="flex flex-col items-center justify-center text-muted-foreground">
                        <Search className="h-10 w-10 mb-4 opacity-20" />
                        <h3 className="text-lg font-medium text-foreground">No parcels found</h3>
                        <p className="mt-1">Try adjusting your filters or search terms.</p>
                      </div>
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
          {data && (
            <div className="px-6 py-4 border-t bg-muted/20 flex items-center justify-between text-sm text-muted-foreground">
              <div>
                Showing {data.items.length} of {data.total} parcels
              </div>
              <div className="flex items-center gap-2">
                <Button 
                  variant="outline" 
                  size="sm" 
                  disabled={params.offset === 0}
                  onClick={() => setParams({ ...params, offset: Math.max(0, (params.offset || 0) - (params.limit || 50)) })}
                >
                  Previous
                </Button>
                <Button 
                  variant="outline" 
                  size="sm"
                  disabled={!data || data.items.length < (params.limit || 50)}
                  onClick={() => setParams({ ...params, offset: (params.offset || 0) + (params.limit || 50) })}
                >
                  Next
                </Button>
              </div>
            </div>
          )}
        </Card>
      </div>
    </AppLayout>
  );
}
