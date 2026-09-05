import { getTestBed } from '@angular/core/testing';

// Setup global de pruebas (opcion "setupFiles" del target "test").
//
// El runner @angular/build:unit-test (Vitest) inicializa por su cuenta el
// entorno (TestBed + plataforma de pruebas para ls plantillas) ANTES de
// cargar este archivo, por lo que aqui NO debe volverse a crear el entorno
// (eso lanzaria NG0400: "platform already created"). En su lugar se aplica
// configuracion global que complementa la suite:
//   - eslint-globals via tsconfig.spec.json ("types": ["vitest/globals"]).
//   - Reglas estrictas de plantilla para que elementos/atributos
//     desconocidos fallen (coincide con la "compilationMode" de CI).
//
// Nota: el TestBed considera hereje re-crear el entorno despues de que el
// runner ya lo hizo; si en el futuro se necesita un entorno distinto
// (p.ej. zoneless), debe configurarse el target "test" en angular.json y no
// aqui.
getTestBed().configureTestingModule({ teardown: { destroyAfterEach: true } });
