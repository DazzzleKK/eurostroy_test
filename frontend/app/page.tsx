import { TelegramInit } from "@/components/TelegramInit";
import { listProducts, type Product } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function CatalogPage() {
  let products: Product[] = [];
  let failed = false;

  try {
    products = await listProducts();
  } catch {
    failed = true;
  }

  return (
    <main>
      <TelegramInit />
      <h1>Каталог</h1>

      {failed ? <p>Каталог временно недоступен.</p> : null}
      {!failed && products.length === 0 ? <p>Пока нет товаров.</p> : null}

      {products.length > 0 ? (
        <ul>
          {products.map((product) => (
            <li key={product.id}>
              <h2>{product.title}</h2>
              <img
                src={product.image_url}
                alt={product.title}
                width={240}
                height={240}
                loading="lazy"
              />
            </li>
          ))}
        </ul>
      ) : null}
    </main>
  );
}
