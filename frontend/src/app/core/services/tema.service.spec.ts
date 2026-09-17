import { TestBed } from '@angular/core/testing';
import { TemaService } from './tema.service';

describe('TemaService', () => {
  beforeEach(() => {
    localStorage.clear();
    document.body.className = '';
    TestBed.configureTestingModule({});
  });

  it('arranca en claro y no marca el body', () => {
    const tema = TestBed.inject(TemaService);
    expect(tema.tema()).toBe('claro');
    expect(document.body.classList.contains('noche')).toBe(false);
  });

  it('alternar pone la clase noche en el body y la guarda', () => {
    const tema = TestBed.inject(TemaService);
    tema.alternar();
    expect(tema.tema()).toBe('noche');
    // El CSS cuelga de `body.noche`: si la clase cambiara de nombre, el tema
    // dejaria de aplicarse sin que nada fallara.
    expect(document.body.classList.contains('noche')).toBe(true);
    expect(localStorage.getItem('intersoft.tema')).toBe('noche');
  });

  it('alternar dos veces vuelve a claro', () => {
    const tema = TestBed.inject(TemaService);
    tema.alternar();
    tema.alternar();
    expect(tema.tema()).toBe('claro');
    expect(document.body.classList.contains('noche')).toBe(false);
  });

  it('aplica la preferencia guardada al arrancar', () => {
    localStorage.setItem('intersoft.tema', 'noche');
    const tema = TestBed.inject(TemaService);
    expect(tema.tema()).toBe('noche');
    expect(document.body.classList.contains('noche')).toBe(true);
  });
});

// ---------------------------------------------------------------------------
// Guarda de regresion del modo noche
//
// El tema cambia los colores reasignando variables CSS en `body.noche`. Un
// color escrito en duro dentro del CSS de un componente NO cambia con el tema:
// en modo noche queda como un parche claro con texto oscuro. Era exactamente
// lo que pasaba en las insignias de estado de facturacion, envios, pedidos e
// inventario.
//
// Se revisa solo el FONDO. Un `color: #fff` sobre un boton de color es
// correcto en los dos temas y no interesa aqui.
// ---------------------------------------------------------------------------

/** `import.meta.glob` es de Vite y no esta en los tipos de TypeScript del
 * proyecto. Se declara aqui en vez de anadir `vite/client` al tsconfig o los
 * tipos de Node: leer el CSS con `fs` obligaria a una dependencia nueva.
 *
 * Tiene que invocarse con el nombre completo y las opciones en linea: Vite lo
 * sustituye en tiempo de transformacion y no funciona a traves de un alias. */
declare global {
  interface ImportMeta {
    glob(
      patron: string,
      opciones: { query: string; import: string; eager: true },
    ): Record<string, string>;
  }
}

const CSS_COMPONENTES = import.meta.glob('/src/app/**/*.css', {
  query: '?raw',
  import: 'default',
  eager: true,
});
const ESTILOS_GLOBALES = import.meta.glob('/src/styles.css', {
  query: '?raw',
  import: 'default',
  eager: true,
});

/** Fondos permitidos pese a ser fijos, con el motivo por el que lo son. */
const EXCEPCIONES = [
  '#111827', // lienzo del video de camaras: oscuro a proposito en ambos temas
  '#ef4444', // punto de grabacion activa
  '#e11d48', // corazon de favorito marcado
];

const AYUDA_TOKENS = [
  'Usa un token del tema en vez de un color fijo:',
  '  superficies  --tarjeta, --papel, --blanco, --neutro-fondo',
  '  estados      --ok-fondo, --error-fondo, --alerta-fondo, --info-fondo, --via-fondo',
  'Si el color debe ser igual en ambos temas, anadelo a EXCEPCIONES con su motivo.',
  '',
].join('\n');

describe('modo noche: los componentes no escriben colores en duro', () => {
  it('carga el CSS que va a revisar', () => {
    // Si el glob deja de encontrar archivos, las pruebas de abajo pasarian en
    // vacio sin proteger nada.
    expect(Object.keys(CSS_COMPONENTES).length).toBeGreaterThan(10);
    expect(Object.keys(ESTILOS_GLOBALES)).toHaveLength(1);
  });

  it('ninguna superficie usa un hex fijo fuera de las excepciones', () => {
    const fondoFijo = /background(?:-color)?\s*:\s*[^;]*?(#[0-9a-fA-F]{3,6})/g;
    const infractores: string[] = [];

    for (const [ruta, css] of Object.entries(CSS_COMPONENTES)) {
      for (const coincidencia of css.matchAll(fondoFijo)) {
        const hex = coincidencia[1].toLowerCase();
        if (!EXCEPCIONES.includes(hex)) infractores.push(`${ruta}: ${hex}`);
      }
    }

    expect(infractores, AYUDA_TOKENS + infractores.join('\n')).toEqual([]);
  });

  it('cada token de color del tema claro tiene su equivalente de noche', () => {
    const estilos = Object.values(ESTILOS_GLOBALES)[0];
    const bloque = (selector: string) => {
      const desde = estilos.indexOf(selector);
      const abre = estilos.indexOf('{', desde);
      return estilos.slice(abre, estilos.indexOf('}', abre));
    };
    const tokens = (texto: string) =>
      new Set(Array.from(texto.matchAll(/(--[a-z0-9-]+)\s*:/g), (m) => m[1]));

    const claro = tokens(bloque(':root'));
    const noche = tokens(bloque('body.noche'));

    // Solo los tokens de COLOR: los de espaciado y tipografia no cambian.
    const deColor = [...claro].filter((t) =>
      /(fondo|borde|tinta|gris|papel|blanco|tarjeta|linea|primario|ok|error|alerta|info|via|neutro)/.test(
        t,
      ),
    );
    const sinVariante = deColor.filter((t) => !noche.has(t));

    expect(
      sinVariante,
      'Sin valor en body.noche, estos tokens conservan el color del tema claro:\n' +
        sinVariante.join('\n'),
    ).toEqual([]);
  });
});
