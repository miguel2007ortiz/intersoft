import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { of, throwError } from 'rxjs';
import { CatalogoService } from '../../../core/services/catalogo.service';
import { AuthService } from '../../../core/services/auth.service';
import { Producto } from '../../../core/models/catalogo.model';
import { ProductosComponent } from './productos.component';

const PRODUCTO: Producto = {
  id: 'p1',
  nombre: 'Camisa Azul',
  descripcion: '',
  sku: 'CAM-1',
  categoria_id: null,
  categoria_nombre: null,
  precio: '35000',
  stock: 10,
  stock_minimo: 5,
  activo: true,
  stock_bajo: false,
  tiene_ventas: false,
  imagen: null,
};

describe('ProductosComponent', () => {
  let catalogo: {
    listarProductos: ReturnType<typeof vi.fn>;
    listarCategorias: ReturnType<typeof vi.fn>;
  };

  beforeEach(() => {
    catalogo = {
      listarProductos: vi.fn(),
      listarCategorias: vi.fn(() => of({ resultados: [] })),
    };
    TestBed.configureTestingModule({
      imports: [ProductosComponent],
      providers: [
        provideRouter([]),
        {
          provide: AuthService,
          useValue: {
            usuario: () => null,
            esAdministrador: () => false,
            tienePermiso: () => false,
          },
        },
        { provide: CatalogoService, useValue: catalogo },
      ],
    });
  });

  const crear = () => {
    const fixture = TestBed.createComponent(ProductosComponent);
    fixture.detectChanges();
    return fixture;
  };

  it('muestra error de carga con estado vacio y reintenta', () => {
    catalogo.listarProductos
      .mockReturnValueOnce(throwError(() => ({ detalle: 'Servidor caido.' })))
      .mockReturnValue(of({ resultados: [PRODUCTO], total: 1 }));
    const fixture = crear();
    let html = (fixture.nativeElement as HTMLElement).textContent ?? '';
    expect(html).toContain('No pudimos cargar los productos');
    expect(html).toContain('Servidor caido.');
    expect(html).not.toContain('Aun no hay productos');

    const boton = Array.from(
      (fixture.nativeElement as HTMLElement).querySelectorAll<HTMLButtonElement>('button'),
    ).find((b) => b.textContent?.includes('Reintentar'));
    boton?.click();
    fixture.detectChanges();
    html = (fixture.nativeElement as HTMLElement).textContent ?? '';
    expect(catalogo.listarProductos).toHaveBeenCalledTimes(2);
    expect(html).toContain('Camisa Azul');
  });

  it('muestra el vacio cuando no hay productos', () => {
    catalogo.listarProductos.mockReturnValue(of({ resultados: [], total: 0 }));
    const html = crear().nativeElement.textContent ?? '';
    expect(html).toContain('Aun no hay productos');
  });

  it('sin resultados por busqueda o filtro ofrece limpiar filtros', () => {
    catalogo.listarProductos.mockReturnValue(of({ resultados: [], total: 0 }));
    const fixture = crear();
    fixture.componentInstance.busqueda.set('zzz');
    fixture.componentInstance.cargar();
    fixture.detectChanges();
    let html = (fixture.nativeElement as HTMLElement).textContent ?? '';
    expect(html).toContain('Sin resultados');
    expect(html).toContain('Limpiar filtros');

    const boton = Array.from(
      (fixture.nativeElement as HTMLElement).querySelectorAll<HTMLButtonElement>('button'),
    ).find((b) => b.textContent?.includes('Limpiar filtros'));
    boton?.click();
    fixture.detectChanges();
    html = (fixture.nativeElement as HTMLElement).textContent ?? '';
    expect(catalogo.listarProductos).toHaveBeenLastCalledWith({
      busqueda: '',
      activo: undefined,
      pagina: 1,
    });
    expect(html).toContain('Aun no hay productos');
  });

  it('pinta "Mostrando X-Y de N" con el total real, no el de la pagina', () => {
    catalogo.listarProductos.mockReturnValue(
      of({
        resultados: [PRODUCTO],
        total: 1024,
        pagina: 2,
        por_pagina: 50,
        total_paginas: 21,
        desde: 51,
        hasta: 100,
      }),
    );
    const html = (crear().nativeElement as HTMLElement).textContent ?? '';
    expect(html).toContain('Mostrando 51-100 de 1.024');
    expect(html).toContain('Pagina 2 de 21');
  });

  it('cambiar de pagina conserva la busqueda y el filtro', () => {
    catalogo.listarProductos.mockReturnValue(
      of({
        resultados: [PRODUCTO],
        total: 200,
        pagina: 1,
        por_pagina: 50,
        total_paginas: 4,
        desde: 1,
        hasta: 50,
      }),
    );
    const fixture = crear();
    fixture.componentInstance.busqueda.set('camisa');
    fixture.componentInstance.filtrar('activos');
    fixture.detectChanges();

    const siguiente = Array.from(
      (fixture.nativeElement as HTMLElement).querySelectorAll<HTMLButtonElement>('button'),
    ).find((b) => b.textContent?.includes('Siguiente'));
    siguiente?.click();
    fixture.detectChanges();

    expect(catalogo.listarProductos).toHaveBeenLastCalledWith({
      busqueda: 'camisa',
      activo: true,
      pagina: 2,
    });
  });

  it('buscar vuelve a la pagina 1', () => {
    catalogo.listarProductos.mockReturnValue(
      of({
        resultados: [PRODUCTO],
        total: 200,
        pagina: 3,
        por_pagina: 50,
        total_paginas: 4,
        desde: 101,
        hasta: 150,
      }),
    );
    const fixture = crear();
    fixture.componentInstance.irAPagina(3);
    fixture.componentInstance.filtrar('inactivos');
    expect(catalogo.listarProductos).toHaveBeenLastCalledWith({
      busqueda: '',
      activo: false,
      pagina: 1,
    });
  });

  it('la miniatura carga en diferido y cae a la imagen de respaldo si falla', () => {
    catalogo.listarProductos.mockReturnValue(
      of({ resultados: [{ ...PRODUCTO, imagen: 'http://api/media/rota.jpg' }], total: 1 }),
    );
    const fixture = crear();
    const img = (fixture.nativeElement as HTMLElement).querySelector<HTMLImageElement>(
      '.miniatura',
    );
    expect(img).not.toBeNull();
    expect(img!.getAttribute('loading')).toBe('lazy');

    img!.dispatchEvent(new Event('error'));
    fixture.detectChanges();
    expect(img!.src).toContain('data:image/svg+xml');
  });
});
