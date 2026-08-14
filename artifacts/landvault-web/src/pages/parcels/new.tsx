import { z } from "zod";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useLocation } from "wouter";
import { AppLayout } from "@/components/layout/app-layout";
import { Card, CardContent, CardDescription, CardHeader, CardTitle, CardFooter } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from "@/components/ui/form";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { useCreateParcel } from "@workspace/api-client-react";
import { ParcelInputParcelType } from "@workspace/api-client-react";
import { toast } from "sonner";
import { Loader2, MapPin, User, FileText } from "lucide-react";
import { useQueryClient } from "@tanstack/react-query";
import { getListParcelsQueryKey, getGetDashboardStatsQueryKey } from "@workspace/api-client-react";

const STATES = [
  "Lagos", "Abuja (FCT)", "Rivers", "Kano", "Ogun", "Oyo", 
  "Delta", "Edo", "Kaduna", "Anambra", "Enugu", "Imo", 
  "Cross River", "Akwa Ibom", "Plateau"
];

const formSchema = z.object({
  owner_name: z.string().min(1, "Owner name is required"),
  owner_phone: z.string().optional(),
  owner_email: z.string().email("Invalid email").optional().or(z.literal("")),
  location_address: z.string().min(1, "Address is required"),
  state: z.string().min(1, "State is required"),
  lga: z.string().min(1, "LGA is required"),
  area_sqm: z.coerce.number().min(1, "Area must be greater than 0"),
  parcel_type: z.nativeEnum(ParcelInputParcelType),
  latitude: z.coerce.number().optional().or(z.literal("").transform(() => undefined)),
  longitude: z.coerce.number().optional().or(z.literal("").transform(() => undefined)),
});

type FormValues = z.infer<typeof formSchema>;

export function ParcelNew() {
  const [, setLocation] = useLocation();
  const queryClient = useQueryClient();
  const createParcel = useCreateParcel();

  const form = useForm<FormValues>({
    resolver: zodResolver(formSchema),
    defaultValues: {
      owner_name: "",
      owner_phone: "",
      owner_email: "",
      location_address: "",
      state: "",
      lga: "",
      area_sqm: 0,
      parcel_type: "residential",
      latitude: undefined,
      longitude: undefined,
    },
  });

  const onSubmit = (data: FormValues) => {
    createParcel.mutate({ data }, {
      onSuccess: (newParcel) => {
        toast.success("Parcel registered successfully", {
          description: `Title Number: ${newParcel.title_number}`,
        });
        queryClient.invalidateQueries({ queryKey: getListParcelsQueryKey() });
        queryClient.invalidateQueries({ queryKey: getGetDashboardStatsQueryKey() });
        setLocation(`/parcels/${newParcel.id}`);
      },
      onError: () => {
        toast.error("Failed to register parcel", {
          description: "Please check the form and try again.",
        });
      }
    });
  };

  return (
    <AppLayout>
      <div className="mx-auto max-w-3xl">
        <div className="mb-6">
          <h1 className="text-3xl font-bold text-foreground">Register New Parcel</h1>
          <p className="text-muted-foreground mt-1 text-lg">Enter the details to create a new land registry record.</p>
        </div>

        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
            <Card>
              <CardHeader className="border-b bg-muted/20">
                <CardTitle className="flex items-center gap-2">
                  <User className="h-5 w-5 text-primary" />
                  Owner Information
                </CardTitle>
                <CardDescription>Primary contact details for the land owner.</CardDescription>
              </CardHeader>
              <CardContent className="grid gap-6 pt-6 md:grid-cols-2">
                <FormField
                  control={form.control}
                  name="owner_name"
                  render={({ field }) => (
                    <FormItem className="md:col-span-2">
                      <FormLabel>Full Name / Company Name *</FormLabel>
                      <FormControl>
                        <Input placeholder="e.g. Adebayo Holdings Ltd." {...field} />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
                <FormField
                  control={form.control}
                  name="owner_phone"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Phone Number</FormLabel>
                      <FormControl>
                        <Input placeholder="+234..." {...field} />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
                <FormField
                  control={form.control}
                  name="owner_email"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Email Address</FormLabel>
                      <FormControl>
                        <Input type="email" placeholder="contact@example.com" {...field} />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="border-b bg-muted/20">
                <CardTitle className="flex items-center gap-2">
                  <MapPin className="h-5 w-5 text-primary" />
                  Location Details
                </CardTitle>
                <CardDescription>Physical location and geopolitical zone.</CardDescription>
              </CardHeader>
              <CardContent className="grid gap-6 pt-6 md:grid-cols-2">
                <FormField
                  control={form.control}
                  name="location_address"
                  render={({ field }) => (
                    <FormItem className="md:col-span-2">
                      <FormLabel>Street Address *</FormLabel>
                      <FormControl>
                        <Input placeholder="Plot 15, Block B, ..." {...field} />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
                <FormField
                  control={form.control}
                  name="state"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>State *</FormLabel>
                      <Select onValueChange={field.onChange} defaultValue={field.value}>
                        <FormControl>
                          <SelectTrigger>
                            <SelectValue placeholder="Select state" />
                          </SelectTrigger>
                        </FormControl>
                        <SelectContent>
                          {STATES.map(s => (
                            <SelectItem key={s} value={s}>{s}</SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                      <FormMessage />
                    </FormItem>
                  )}
                />
                <FormField
                  control={form.control}
                  name="lga"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Local Government Area (LGA) *</FormLabel>
                      <FormControl>
                        <Input placeholder="e.g. Ikeja" {...field} />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
                <FormField
                  control={form.control}
                  name="latitude"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Latitude (Optional)</FormLabel>
                      <FormControl>
                        <Input type="number" step="any" placeholder="6.5244" {...field} />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
                <FormField
                  control={form.control}
                  name="longitude"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Longitude (Optional)</FormLabel>
                      <FormControl>
                        <Input type="number" step="any" placeholder="3.3792" {...field} />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="border-b bg-muted/20">
                <CardTitle className="flex items-center gap-2">
                  <FileText className="h-5 w-5 text-primary" />
                  Parcel Specifications
                </CardTitle>
                <CardDescription>Size and designated usage.</CardDescription>
              </CardHeader>
              <CardContent className="grid gap-6 pt-6 md:grid-cols-2">
                <FormField
                  control={form.control}
                  name="area_sqm"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Area (Square Meters) *</FormLabel>
                      <FormControl>
                        <Input type="number" {...field} />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
                <FormField
                  control={form.control}
                  name="parcel_type"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Land Use Type *</FormLabel>
                      <Select onValueChange={field.onChange} defaultValue={field.value}>
                        <FormControl>
                          <SelectTrigger>
                            <SelectValue placeholder="Select type" />
                          </SelectTrigger>
                        </FormControl>
                        <SelectContent>
                          {Object.values(ParcelInputParcelType).map(t => (
                            <SelectItem key={t} value={t}>{t.charAt(0).toUpperCase() + t.slice(1)}</SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              </CardContent>
              <CardFooter className="border-t bg-muted/20 py-4 flex justify-end gap-4">
                <Button type="button" variant="outline" onClick={() => setLocation("/parcels")}>
                  Cancel
                </Button>
                <Button type="submit" disabled={createParcel.isPending}>
                  {createParcel.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                  Register Parcel
                </Button>
              </CardFooter>
            </Card>
          </form>
        </Form>
      </div>
    </AppLayout>
  );
}
