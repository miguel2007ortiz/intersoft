import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { of } from 'rxjs';
import { CatalogoService } from '../../core/services/catalogo.service';
import { AuthService } from '../../core/services/auth.service';
import { InventarioComponent } from './inventario.component';

const PRODUCTO = {
  id: 'p1',
  nombre: 'Camisa Azul',
  sku: 'CAM-1',
  categoria: 'Ropa',
  precio: '35000',
  stock: 2,
  stock_minimo: 10,
  stock_bajo: true,
};

const PAGINA = {
  resultados: [PRODUCTO],
  total: 320,
  pagina: 1,
  por_pagina: 50,
  total_paginas: 7,
  desde: 1,
  hasta: 50,
};

describe('InventarioComponent', () => {
  let catalogo: {
    listarInventario: ReturnType<typeof vi.fn>;
    listarMovimientos: ReturnType<typeof vi.fn>;
  };

  beforeEach(() => {
    catalogo = {
      listarInventario: vi.fn(() => of(PAGINA)),
      listarMovimientos: vi.fn(() => of({ resultados: [], total: 0 })),
    };
    TestBed.configureTestingModule({
      imports: [InventarioComponent],
      providers: [
        provideRouter([]),
        {
          provide: AuthService,
          useValue: {
            usuario: () => null,
            esAdministrador: () => false,
            tienePermiso: () => true,
          },
        },
        { provide: CatalogoService, useValue: catalogo },
      ],
    });
  });

  const crear = () => {
    const fixture = TestBed.createComponent(InventarioComponent);
    fixture.detectChanges();
    return fixture;
  };

  it('pinta el total real del filtro, no el tamano de la pagina', () => {
    const html = (crear().nativeElement as HTMLElement).textContent ?? '';
    expect(html).toContain('Mostrando 1-50 de 320');
    expect(html).toContain('Pagina 1 de 7');
  });

  it('cambiar de pagina conserva la busqueda y el filtro de stock bajo', () => {
    const fixture = crear();
    fixture.componentInstance.busquedaProducto = 'camisa';
    fixture.componentInstance.filtroStockBajo = true;
    fixture.componentInstance.filtrarStockBajo();
    fixture.detectChanges();

    const siguiente = Array.from(
      (fixture.nativeElement as HTMLElement).querySelectorAll<HTMLButtonElement>('button'),
    ).find((b) => b.textContent?.includes('Siguiente'));
    siguiente?.click();
    fixture.detectChanges();

    expect(catalogo.listarInventario).toHaveBeenLastCalledWith({
      busqueda: 'camisa',
      stock_bajo: true,
      pagina: 2,
    });
  });

  it('los dos filtros se mandan juntos al servidor', () => {
    const fixture = crear();
    fixture.componentInstance.busquedaProducto = 'cam';
    fixture.componentInstance.filtroStockBajo = true;
    fixture.componentInstance.cargarProductos();

    // Combinarlos en el cliente sobre la pagina ya recortada solo miraria los
    // 50 primeros productos: por eso viajan los dos al backend.
    expect(catalogo.listarInventario).toHaveBeenLastCalledWith({
      busqueda: 'cam',
      stock_bajo: true,
      pagina: 1,
    });
  });

  it('marcar "solo stock bajo" vuelve a la primera pagina', () => {
    const fixture = crear();
    fixture.componentInstance.irAPagina(4);
    fixture.componentInstance.filtroStockBajo = true;
    fixture.componentInstance.filtrarStockBajo();

    expect(catalogo.listarInventario).toHaveBeenLastCalledWith({
      busqueda: undefined,
      stock_bajo: true,
      pagina: 1,
    });
  });
});
