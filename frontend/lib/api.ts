export type Product = {
  id: string;
  title: string;
  image_url: string;
  created_at: string;
};

type ProductList = {
  items: Product[];
  next_cursor: string | null;
};

const BACKEND_URL = process.env.BACKEND_INTERNAL_URL ?? "http://localhost:8000";

export async function listProducts(limit = 100): Promise<Product[]> {
  const url = new URL("/api/products", BACKEND_URL);
  url.searchParams.set("limit", String(limit));

  const response = await fetch(url, { cache: "no-store" });
  if (!response.ok) {
    throw new Error(`catalog request failed with status ${response.status}`);
  }

  const body = (await response.json()) as ProductList;
  return body.items;
}
